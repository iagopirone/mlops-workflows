"""Turn a saved Florence-2 run into detection files and annotated images.

Runs in the project environment (not in the Florence-2 venv), from the
repository root:

    uv run python -m experiments.florence2.render \
        --run-dir experiments/florence2/outputs/<run-id>

For every completed task it validates the structured output with
``florence_to_detections``, saves a ``DetectionReference`` JSON and draws it with
the existing ``DetectionVisualizationComponent``. ``summary.json`` records each
task's status (``error``, ``invalid_output``, ``no_detections`` or
``detections``), labels, box area fractions and file hashes. ``run.json`` and the
raw outputs are only read.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from experiments.florence2.florence_detections import (
    FlorenceOutputError,
    area_fraction,
    class_source,
    florence_to_detections,
)
from mlops_workflows.artifacts.detection.detection_content import DetectionContent
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.components.detection_visualization.detection_visualization_component import (
    DetectionVisualizationComponent,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(run_dir: Path) -> dict[str, object]:
    """Convert and draw every task of one run; return and save the summary."""
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    image_info = run["image"]
    image = ImageReference(name="input", location=image_info["path"])
    if sha256(Path(image.location)) != image_info["sha256"]:
        raise ValueError("The image differs from the one used in the run (SHA-256).")
    height, width = image.materialize().data.shape[:2]
    if (width, height) != (image_info["width"], image_info["height"]):
        raise ValueError("OpenCV and PIL disagree on the image size.")

    tasks = []
    for task in run["tasks"]:
        entry = {
            "index": task["index"],
            "prompt": task["prompt"],
            "class_source": class_source(task["task"]),
        }
        if task["status"] != "completed":
            tasks.append(entry | {"status": "error", "error": task.get("error")})
            continue
        try:
            detections = florence_to_detections(
                task["parsed"], task["task"], width, height, task.get("phrase")
            )
        except FlorenceOutputError as exc:
            tasks.append(entry | {"status": "invalid_output", "error": str(exc)})
            continue
        if not detections:
            tasks.append(entry | {"status": "no_detections"})
            continue
        prefix = f"task-{task['index']}"
        reference = DetectionReference(
            name=f"{prefix}-detections",
            location=str(run_dir / f"{prefix}-detections.json"),
        )
        DetectionContent(data=detections).dematerialize(reference)
        annotated = ImageReference(
            name=f"{prefix}-annotated",
            location=str(run_dir / f"{prefix}-annotated.png"),
        )
        component = DetectionVisualizationComponent(annotated)
        component.execute(component.prepare([image, reference]))
        tasks.append(
            entry
            | {
                "status": "detections",
                "detections": [
                    {
                        "cls": d.cls,
                        "box": d.box,
                        "area_fraction": round(area_fraction(d.box, width, height), 4),
                    }
                    for d in detections
                ],
                "detections_file": Path(reference.location).name,
                "detections_sha256": sha256(Path(reference.location)),
                "annotated_image": Path(annotated.location).name,
                "annotated_sha256": sha256(Path(annotated.location)),
            }
        )

    summary = {"run_json_sha256": sha256(run_dir / "run.json"), "tasks": tasks}
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        summary = render(args.run_dir)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    for task in summary["tasks"]:
        print(f"{task['prompt']}: {task['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
