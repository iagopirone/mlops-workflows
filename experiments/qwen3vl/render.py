"""Turn a saved Qwen3-VL run into detection files and annotated images.

Runs in the project environment, from the repository root:

    uv run python -m experiments.qwen3vl.render \
        --run-dir experiments/qwen3vl/outputs/<run-id> --convention relative_1000

The convention must be chosen explicitly (documented: ``relative_1000``) and is
checked against the raw coordinates (``coordinate_evidence``). For every prompt
it validates the answer with ``qwen_to_detections``, saves a
``DetectionReference`` JSON and draws it with the existing
``DetectionVisualizationComponent``. ``summary.json`` records each prompt's
status (``error``, ``text_only`` for descriptive prompts, ``invalid_output``,
``no_detections`` or ``detections``), the evidence and file hashes. Run files are only read.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from experiments.qwen3vl.qwen_detections import (
    CONVENTIONS,
    QwenOutputError,
    coordinate_evidence,
    qwen_to_detections,
)
from mlops_workflows.artifacts.detection.detection_content import DetectionContent
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.components.detection_visualization.detection_visualization_component import (
    DetectionVisualizationComponent,
)

# Prompts whose answer is expected to contain boxes; others are descriptive.
GROUNDING_PREFIX = "ground_"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(run_dir: Path, convention: str) -> dict[str, object]:
    """Convert and draw every grounding answer of one run; save the summary."""
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    image = ImageReference(name="input", location=run["image"]["path"])
    if sha256(Path(image.location)) != run["image"]["sha256"]:
        raise ValueError("The image differs from the one used in the run (SHA-256).")
    height, width = image.materialize().data.shape[:2]

    prompts = []
    for prompt in run["prompts"]:
        name = prompt["name"]
        entry = {"name": name, "prompt": prompt["prompt"]}
        if prompt["returncode"] != 0:
            prompts.append(entry | {"status": "error"})
            continue
        answer = (run_dir / prompt["stdout_file"]).read_text(encoding="utf-8")
        evidence = coordinate_evidence(answer, width, height)
        entry["coordinate_evidence"] = evidence
        if not name.startswith(GROUNDING_PREFIX):
            prompts.append(entry | {"status": "text_only"})
            continue
        try:
            detections = qwen_to_detections(answer, convention, width, height)
        except QwenOutputError as exc:
            prompts.append(entry | {"status": "invalid_output", "error": str(exc)})
            continue
        if not detections:
            prompts.append(entry | {"status": "no_detections"})
            continue
        reference = DetectionReference(
            name=f"{name}-detections", location=str(run_dir / f"{name}-detections.json")
        )
        DetectionContent(data=detections).dematerialize(reference)
        annotated = ImageReference(
            name=f"{name}-annotated", location=str(run_dir / f"{name}-annotated.png")
        )
        component = DetectionVisualizationComponent(annotated)
        component.execute(component.prepare([image, reference]))
        prompts.append(
            entry
            | {
                "status": "detections",
                "labels": sorted({d.cls for d in detections}),
                "detections": [{"cls": d.cls, "box": d.box} for d in detections],
                "detections_file": Path(reference.location).name,
                "detections_sha256": sha256(Path(reference.location)),
                "annotated_image": Path(annotated.location).name,
                "annotated_sha256": sha256(Path(annotated.location)),
            }
        )

    summary = {
        "run_json_sha256": sha256(run_dir / "run.json"),
        "convention": convention,
        "image_size": [width, height],
        "prompts": prompts,
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--convention", choices=CONVENTIONS, required=True)
    args = parser.parse_args(argv)
    try:
        summary = render(args.run_dir, args.convention)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    for prompt in summary["prompts"]:
        print(f"{prompt['name']}: {prompt['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
