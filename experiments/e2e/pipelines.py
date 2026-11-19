"""Run the two end-to-end pipelines with the existing components.

* YOLO: ``ImageReference`` → ``ObjectDetectionComponent`` → ``DetectionReference``
  → ``DetectionVisualizationComponent`` → annotated ``ImageReference``.
* MIRAGE: the official model runs out of process (``run_poc.py --execute`` on a
  GPU host). Its saved answer is used as a ``TextReference`` →
  ``TextDetectionParsingComponent`` → ``DetectionReference`` →
  ``DetectionVisualizationComponent``. Nothing here runs or simulates MIRAGE.

Each function returns a ``PipelineRun`` whose status separates infrastructure
failures, invalid responses and produced detections. Whether detections are
correct is measured later against human annotations.
"""

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from experiments.e2e.training_format import TrainingFormatError
from mlops_workflows.artifacts.detection.detection_content import DetectionContent
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.artifacts.report.execution_report import (
    ArtifactRecord,
    InferenceCheck,
    PipelineRun,
)
from mlops_workflows.artifacts.text.text_content import TextContent
from mlops_workflows.artifacts.text.text_reference import TextReference
from mlops_workflows.components.detection_visualization.detection_visualization_component import (
    DetectionVisualizationComponent,
)
from mlops_workflows.components.object_detection.object_detection_component import (
    ObjectDetectionComponent,
)
from mlops_workflows.components.object_detection.object_detector import ObjectDetector
from mlops_workflows.components.text_detection_parsing.text_detection_parser import (
    TextDetectionParser,
)
from mlops_workflows.components.text_detection_parsing.text_detection_parsing_component import (
    TextDetectionParsingComponent,
)

OFFICIAL_OUTPUT_MARKERS = ("---Output---", "Text Output:")


def file_sha256(path: Path) -> str:
    """Return the SHA-256 of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(kind: str, name: str, location: str) -> ArtifactRecord:
    """Describe an existing file with its SHA-256."""
    return ArtifactRecord(
        kind=kind, name=name, location=location, sha256=file_sha256(Path(location))
    )


def _ref_record(
    kind: str, reference: ImageReference | DetectionReference | TextReference
):
    return record(kind, reference.name, reference.location)


def _visualize(
    image: ImageReference, detections: DetectionReference, output_dir: Path, name: str
) -> ImageReference:
    annotated = ImageReference(
        name=f"{name}-annotated", location=str(output_dir / "annotated.png")
    )
    component = DetectionVisualizationComponent(annotated)
    return component.execute(component.prepare([image, detections]))[0]


def run_yolo_pipeline(
    image: ImageReference,
    image_id: str,
    detector: ObjectDetector,
    model_key: str,
    output_dir: Path,
    inference_checks: list[InferenceCheck],
) -> PipelineRun:
    """Detect objects in one image and draw them; failures are recorded.

    ``inference_checks`` describe why ``detector`` is the real model (built by
    the report tool); they are required for a successful run.
    """
    detections = DetectionReference(
        name=f"{image_id}-detections", location=str(output_dir / "detections.json")
    )
    common = {
        "pipeline": "yolo",
        "experiment": "detection",
        "model_key": model_key,
        "image_id": image_id,
        "class_source": "model",
        "inputs": [_ref_record("image", image)],
        "evidence": [],
        "inference_checks": inference_checks,
    }
    started = time.perf_counter()
    try:
        component = ObjectDetectionComponent(detector, detections)
        component.execute(component.prepare([image]))
        annotated = _visualize(image, detections, output_dir, image_id)
        count = len(detections.materialize().data)
    except Exception as exc:  # noqa: BLE001 - any failure must be recorded, not hidden
        return PipelineRun(
            **common,
            status="infrastructure_failure",
            error=f"{type(exc).__name__}: {exc}",
            detection_count=None,
            duration_seconds=time.perf_counter() - started,
            outputs=[],
        )
    return PipelineRun(
        **common,
        status="succeeded",
        error=None,
        detection_count=count,
        duration_seconds=time.perf_counter() - started,
        outputs=[_ref_record("detection", detections), _ref_record("image", annotated)],
    )


@dataclass(frozen=True)
class MirageExpectations:
    """What a real run of the approved MIRAGE setup must show in its run.json."""

    official_revision: str
    checkpoint_name: str
    min_gpu_memory_mib: int


def mirage_inference_checks(
    run: dict[str, object], stdout: str, prompt: str, expected: MirageExpectations
) -> list[InferenceCheck]:
    """Return the real-inference checks of one run_poc.py execution."""
    repo = run.get("official_repo") or {}
    parameters = run.get("parameters") or {}
    environment = run.get("environment") or {}
    model_path = str(parameters.get("model_path_resolved") or "")
    peak = environment.get("gpu_memory_peak_mib")

    def check(name: str, passed: bool, detail: str) -> InferenceCheck:
        return InferenceCheck(name=name, passed=bool(passed), detail=detail)

    return [
        check(
            "process_completed",
            run.get("returncode") == 0,
            f"returncode {run.get('returncode')}",
        ),
        check(
            "official_output_markers",
            all(marker in stdout for marker in OFFICIAL_OUTPUT_MARKERS),
            f"stdout contains {list(OFFICIAL_OUTPUT_MARKERS)}",
        ),
        check(
            "official_code_revision",
            repo.get("revision") == expected.official_revision
            and repo.get("dirty") is False,
            f"revision {repo.get('revision')}, dirty {repo.get('dirty')}",
        ),
        check(
            "checkpoint",
            Path(model_path).name == expected.checkpoint_name
            and parameters.get("allow_remote_model") is False,
            f"model path {model_path!r}, remote {parameters.get('allow_remote_model')}",
        ),
        check(
            "prompt",
            run.get("prompt") == prompt,
            "run.json prompt equals the experiment prompt file",
        ),
        check(
            "offline",
            environment.get("hf_hub_offline") == "1",
            f"HF_HUB_OFFLINE={environment.get('hf_hub_offline')}",
        ),
        check("gpu_present", bool(environment.get("gpu")), f"{environment.get('gpu')}"),
        check(
            "gpu_memory_loaded",
            isinstance(peak, int) and peak >= expected.min_gpu_memory_mib,
            f"peak {peak} MiB sampled during the run (minimum "
            f"{expected.min_gpu_memory_mib} MiB)",
        ),
    ]


def _check_run_image(run: dict[str, object], image: ImageReference) -> None:
    """Abort when the run cannot be tied to exactly this image."""
    images = run.get("images") or []
    answer_image = run.get("answer_image")
    if answer_image is None or len(images) != 1:
        raise ValueError("run.json does not associate the answer with one image.")
    if Path(str(answer_image)).name != Path(image.location).name:
        raise ValueError(
            f"run.json answer image {answer_image!r} is not {image.location!r}."
        )
    height, width = image.materialize().data.shape[:2]
    if (images[0].get("width"), images[0].get("height")) != (width, height):
        raise ValueError("Image size in run.json differs from the local image.")


def run_mirage_pipeline(
    run_dir: Path,
    image: ImageReference,
    image_id: str,
    experiment: str,
    model_key: str,
    coordinate_format: str,
    output_dir: Path,
    prompt: str,
    expected: MirageExpectations,
    convert: Callable[[str], str] | None = None,
) -> PipelineRun:
    """Turn one saved MIRAGE answer into detections and an annotated image.

    ``convert`` rewrites the answer before parsing (the experimental
    training-format adapter); the converted text is saved as a separate
    ``TextReference`` and the class then comes from the prompt. Raises
    ``ValueError`` when the run belongs to another image: that is a setup
    error, not a model result. The run files are never modified.
    """
    evidence = [
        record("file", name, str(run_dir / name))
        for name in ("run.json", "stdout.txt", "stderr.txt", "gpu-memory.csv")
        if (run_dir / name).is_file()
    ]
    inputs = [_ref_record("image", image)]
    common = {
        "pipeline": "mirage",
        "experiment": experiment,
        "model_key": model_key,
        "image_id": image_id,
        "class_source": "prompt" if convert else "model",
        "inputs": inputs,
        "evidence": evidence,
    }

    def failure(status, error, duration, checks, outputs=()) -> PipelineRun:
        return PipelineRun(
            **common,
            status=status,
            error=error,
            detection_count=None,
            duration_seconds=duration,
            outputs=list(outputs),
            inference_checks=checks,
        )

    run_file = run_dir / "run.json"
    if not run_file.is_file():
        return failure("infrastructure_failure", "run.json not found.", None, [])
    run = json.loads(run_file.read_text(encoding="utf-8"))
    duration = run.get("duration_seconds")
    _check_run_image(run, image)

    stdout_file = run_dir / "stdout.txt"
    stdout = stdout_file.read_text(encoding="utf-8") if stdout_file.is_file() else ""
    checks = mirage_inference_checks(run, stdout, prompt, expected)
    if run.get("returncode") != 0:
        error = f"demo.py exited with code {run.get('returncode')}; see stderr.txt."
        return failure("infrastructure_failure", error, duration, checks)
    answer_file = run_dir / "answer.txt"
    if not answer_file.is_file():
        error = "No 'Text Output:' marker in stdout; no answer was extracted."
        return failure("infrastructure_failure", error, duration, checks)
    failed = [check.name for check in checks if not check.passed]
    if failed:
        error = f"Insufficient evidence of real inference: {', '.join(failed)}."
        return failure("infrastructure_failure", error, duration, checks)

    answer = TextReference(name=f"{image_id}-answer", location=str(answer_file))
    inputs.append(_ref_record("text", answer))
    outputs = []
    parsed_input = answer
    if convert is not None:
        try:
            converted_text = convert(answer.materialize().data)
        except TrainingFormatError as exc:
            return failure("invalid_response", str(exc), duration, checks)
        parsed_input = TextReference(
            name=f"{image_id}-answer-converted",
            location=str(output_dir / "answer-converted.json"),
        )
        TextContent(data=converted_text).dematerialize(parsed_input)
        outputs.append(_ref_record("text", parsed_input))

    detections = DetectionReference(
        name=f"{image_id}-detections", location=str(output_dir / "detections.json")
    )
    parsing = TextDetectionParsingComponent(
        TextDetectionParser(coordinate_format), detections
    )
    try:
        parsing.execute(parsing.prepare([image, parsed_input]))
    except ValueError as exc:
        return failure("invalid_response", str(exc), duration, checks, outputs)

    annotated = _visualize(image, detections, output_dir, image_id)
    return PipelineRun(
        **common,
        status="succeeded",
        error=None,
        detection_count=len(detections.materialize().data),
        duration_seconds=duration,
        outputs=[
            *outputs,
            _ref_record("detection", detections),
            _ref_record("image", annotated),
        ],
        inference_checks=checks,
    )


@dataclass(frozen=True)
class QwenExpectations:
    """What a real run of the approved Qwen3-VL setup must show in its run.json."""

    files_sha256: dict[str, str]
    llama_cpp_commit: str
    config: str
    generation: tuple[str, ...]
    min_process_rss_mib: float


def qwen_inference_checks(
    run: dict[str, object],
    prompt: dict[str, object],
    stderr: str,
    image_sha256: str,
    expected: QwenExpectations,
) -> list[InferenceCheck]:
    """Return the real-inference checks of one run_qwen.py prompt."""
    limit = run.get("memory_limit") or {}
    oom = str(limit.get("oom_events") or "")
    rss = (prompt.get("process_peak_mib") or {}).get("VmHWM")

    def check(name: str, passed: bool, detail: str) -> InferenceCheck:
        return InferenceCheck(name=name, passed=bool(passed), detail=detail)

    return [
        check("process_completed", prompt.get("returncode") == 0,
              f"returncode {prompt.get('returncode')}"),
        check("image_encoded", "mtmd batch encoding done" in stderr,
              "llama.cpp logged 'mtmd batch encoding done'"),
        check("weights", (run.get("model") or {}).get("files_sha256") == expected.files_sha256,
              "GGUF SHA-256 equal to the published files"),
        check("runtime", (run.get("runtime") or {}).get("llama_cpp_commit") == expected.llama_cpp_commit,
              f"llama.cpp commit {(run.get('runtime') or {}).get('llama_cpp_commit')}"),
        check("configuration",
              run.get("config") == expected.config
              and tuple(run.get("generation") or ()) == expected.generation,
              f"config {run.get('config')}"),
        check("image", (run.get("image") or {}).get("sha256") == image_sha256,
              "image SHA-256 equal to the selected image"),
        check("memory_cap",
              limit.get("memory.max") not in (None, "max")
              and limit.get("memory.swap.max") == "0"
              and "oom_kill 0" in oom,
              f"memory.max {limit.get('memory.max')}, swap.max {limit.get('memory.swap.max')}"),
        check("weights_loaded",
              isinstance(rss, int | float) and rss >= expected.min_process_rss_mib,
              f"process peak RSS {rss} MiB (minimum {expected.min_process_rss_mib})"),
    ]  # fmt: skip


def run_qwen_pipeline(
    run_dir: Path,
    prompt_name: str,
    image: ImageReference,
    image_id: str,
    experiment: str,
    model_key: str,
    class_source: str,
    output_dir: Path,
    expected: QwenExpectations,
) -> PipelineRun:
    """Turn one saved Qwen3-VL answer into detections and an annotated image.

    The answer (stdout of llama-mtmd-cli) is used as a ``TextReference`` and
    converted by ``qwen_to_detections`` (relative 0-1000 -> pixels). Detections
    keep the model's original labels. An answer that is not a valid box list is
    an ``invalid_response`` with zero usable detections; missing evidence of a
    real inference is an ``infrastructure_failure``.
    """
    from experiments.qwen3vl.qwen_detections import QwenOutputError, qwen_to_detections

    common = {
        "pipeline": "qwen3vl",
        "experiment": experiment,
        "model_key": model_key,
        "image_id": image_id,
        "class_source": class_source,
        "inputs": [_ref_record("image", image)],
    }

    def failure(status, error, duration, checks, evidence) -> PipelineRun:
        return PipelineRun(**common, status=status, error=error, detection_count=None,
                           duration_seconds=duration, outputs=[], evidence=evidence,
                           inference_checks=checks)  # fmt: skip

    run_file = run_dir / "run.json"
    if not run_file.is_file():
        return failure("infrastructure_failure", "run.json not found.", None, [], [])
    run = json.loads(run_file.read_text(encoding="utf-8"))
    prompt = next((p for p in run.get("prompts", []) if p["name"] == prompt_name), None)
    if prompt is None:
        return failure("infrastructure_failure", f"Prompt {prompt_name!r} did not run.",
                       None, [], [record("file", "run.json", str(run_file))])  # fmt: skip
    stdout_file, stderr_file = (
        run_dir / prompt["stdout_file"],
        run_dir / prompt["stderr_file"],
    )
    evidence = [record("file", name.name, str(name))
                for name in (run_file, stdout_file, stderr_file) if name.is_file()]  # fmt: skip
    stderr = stderr_file.read_text(encoding="utf-8") if stderr_file.is_file() else ""
    checks = qwen_inference_checks(
        run, prompt, stderr, file_sha256(Path(image.location)), expected
    )
    duration = prompt.get("wall_seconds")
    failed = [check.name for check in checks if not check.passed]
    if failed or not stdout_file.is_file():
        error = f"Missing evidence of a completed real inference: {', '.join(failed) or 'stdout'}."
        return failure("infrastructure_failure", error, duration, checks, evidence)

    answer = TextReference(name=f"{image_id}-{prompt_name}", location=str(stdout_file))
    common["inputs"].append(_ref_record("text", answer))
    height, width = image.materialize().data.shape[:2]
    try:
        detections = qwen_to_detections(
            answer.materialize().data, "relative_1000", width, height
        )
    except QwenOutputError as exc:
        return failure("invalid_response", f"Inference completed with invalid output "
                       f"(zero usable detections): {exc}", duration, checks, evidence)  # fmt: skip

    reference = DetectionReference(
        name=f"{image_id}-detections", location=str(output_dir / "detections.json")
    )
    DetectionContent(data=detections).dematerialize(reference)
    annotated = _visualize(image, reference, output_dir, image_id)
    return PipelineRun(
        **common,
        status="succeeded",
        error=None,
        detection_count=len(detections),
        duration_seconds=duration,
        outputs=[_ref_record("detection", reference), _ref_record("image", annotated)],
        evidence=evidence,
        inference_checks=checks,
    )
