"""Build the end-to-end execution report from real model runs.

Run from the repository root, in the project environment, AFTER the MIRAGE runs
were copied back from the GPU host:

    uv run python -m experiments.e2e.build_report --manifest e2e-manifest.json

The tool runs the real YOLO (``YoloDetector`` with the ONNX file in the
manifest) on the selected images, turns each saved MIRAGE run into detections
with the existing components, evaluates every pipeline and experiment with the
offline evaluator, and saves an ``ExecutionReport`` artifact. A model name in
metadata is not accepted as proof of inference: every run carries explicit
real-inference checks, and runs without them cannot count as model answers.
"""

import argparse
import json
import platform
import sys
from datetime import UTC, datetime
from functools import partial
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from experiments.e2e.bccd_annotations import CLASSES, check_class_names
from experiments.e2e.pipelines import (
    MirageExpectations,
    QwenExpectations,
    file_sha256,
    record,
    run_mirage_pipeline,
    run_qwen_pipeline,
    run_yolo_pipeline,
)
from experiments.e2e.training_format import training_answer_to_json
from experiments.e2e.yolo_evaluation import evaluate_detection_references
from experiments.mirage.evaluate_detections import box_iou, load_ground_truth
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.artifacts.report.execution_report import (
    Evaluation,
    ExecutionReport,
    InferenceCheck,
    ModelIdentity,
    PipelineRun,
)
from mlops_workflows.artifacts.report.execution_report_content import (
    ExecutionReportContent,
)
from mlops_workflows.artifacts.report.execution_report_reference import (
    ExecutionReportReference,
)
from mlops_workflows.components.object_detection.object_detector import ObjectDetector

# Same-label boxes overlapping this much count as near-duplicates.
NEAR_DUPLICATE_IOU = 0.5
# Pre-registered (E8) values every manifest must state before any real run.
REQUIRED_CRITERIA = (
    "iou_threshold",
    "positive_min_valid_response_rate",
    "positive_min_precision",
    "positive_min_recall",
    "positive_min_mean_matched_iou",
    "positive_max_false_positives_per_image",
    "negative_max_valid_response_rate",
    "negative_max_precision",
)


class Settings(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class YoloSettings(Settings):
    model_path: str
    confidence_threshold: float = Field(ge=0, le=1)
    iou_threshold: float = Field(ge=0, le=1)


class MirageExperiment(Settings):
    name: str = Field(min_length=1)
    prompt_file: str
    runs_dir: str
    prompt_class: str | None = None
    coordinate_format: str = "normalized_padded_square"


class MirageSettings(Settings):
    model_name: str
    checkpoint_name: str
    checkpoint_revision: str
    clip_revision: str
    official_revision: str
    min_gpu_memory_mib: int = Field(gt=0)
    experiments: list[MirageExperiment] = Field(min_length=1)


class QwenSettings(Settings):
    model_name: str
    revision: str
    files_sha256: dict[str, str]
    llama_cpp_release: str
    llama_cpp_commit: str
    config: str
    generation: list[str]
    min_process_rss_mib: float = Field(gt=0)
    runs_dir: str
    label_mapping: dict[str, str]


# Experiment A (joint detection, labels from the model) and B (one prompt per
# class, label given by the prompt): prompt name in run_qwen.py and class.
QWEN_JOINT = ("joint_detection", "ground_all")
QWEN_CONDITIONED = {
    "RBC": "ground_rbc",
    "WBC": "ground_wbc",
    "Platelets": "ground_platelet",
}


class Manifest(Settings):
    run_id: str = Field(min_length=1)
    output_dir: str
    annotations: str
    selection: str
    images_dir: str
    criteria: dict[str, float]
    yolo: YoloSettings | None = None
    mirage: MirageSettings | None = None
    qwen3vl: QwenSettings | None = None
    deviations: list[str] = Field(default_factory=list)


def duplicate_counts(predictions: list[dict[str, object]]) -> tuple[int, int]:
    """Exact duplicate boxes and same-label pairs with IoU >= 0.5 (distinct boxes)."""
    keys = [(p["cls"], tuple(p["box"])) for p in predictions]
    exact = len(keys) - len(set(keys))
    near = sum(
        1
        for i, a in enumerate(predictions)
        for b in predictions[i + 1 :]
        if a["cls"] == b["cls"]
        and a["box"] != b["box"]
        and box_iou(a["box"], b["box"]) >= NEAR_DUPLICATE_IOU
    )
    return exact, near


def _evaluate(
    pipeline: str,
    experiment: str,
    class_source: str,
    coordinate_format: str,
    runs: list[PipelineRun],
    ground_truth: dict[str, dict[str, object]],
    manifest: Manifest,
    out: Path,
    class_aware: bool = True,
    subset: str = "all_images",
    label_mapping: dict[str, str] | None = None,
) -> Evaluation:
    """Evaluate one pipeline/experiment and add derived counts to the summary.

    Only successful runs provide detections. With ``subset="all_images"``
    images with an invalid answer or an infrastructure failure get none (all
    their annotations are false negatives); ``"valid_responses"`` keeps only
    images whose run succeeded and is reported next to, never instead of, it.
    """
    if subset == "valid_responses":
        kept = {run.image_id for run in runs if run.status == "succeeded"}
        ground_truth = {k: v for k, v in ground_truth.items() if k in kept}
    elif subset == "completed_inferences":
        kept = {r.image_id for r in runs if r.status != "infrastructure_failure"}
        ground_truth = {k: v for k, v in ground_truth.items() if k in kept}
    references = {
        run.image_id: DetectionReference(
            name=f"{run.image_id}-detections",
            location=next(o.location for o in run.outputs if o.kind == "detection"),
        )
        for run in runs
        if run.status == "succeeded" and run.image_id in ground_truth
    }
    iou = manifest.criteria["iou_threshold"]
    result = evaluate_detection_references(
        ground_truth, references, iou, class_aware, label_mapping
    )
    annotated = [image for image in result["images"] if image["annotated_objects"]]
    statuses = [run.status for run in runs]
    predictions = [p for image in result["images"] for p in image["predictions"]]
    exact = near = 0
    for image in result["images"]:
        image_exact, image_near = duplicate_counts(image["predictions"])
        exact, near = exact + image_exact, near + image_near
    derived = {
        "runs": len(runs),
        "succeeded_runs": statuses.count("succeeded"),
        "completed_inferences_with_invalid_output": statuses.count("invalid_response"),
        "infrastructure_failures": statuses.count("infrastructure_failure"),
        "valid_response_rate": statuses.count("succeeded") / len(runs)
        if runs
        else None,
        "images_with_correct_localization": sum(
            1 for image in annotated if image["true_positives"] > 0
        ),
        "images_with_annotations": len(annotated),
        "mean_false_positives_per_image": (
            result["summary"]["false_positives"] / len(result["images"])
            if result["images"]
            else None
        ),
        "out_of_vocabulary_predictions": sum(
            1 for p in predictions if p["cls"] not in CLASSES
        ),
        "exact_duplicate_boxes": exact,
        "near_duplicate_pairs_iou50": near,
    }
    result["summary"] = result["summary"] | derived
    result["label_mapping"] = label_mapping or {}
    mode = "class-aware" if class_aware else "class-agnostic"
    name = f"{pipeline}-{experiment.replace(':', '-')}-{mode}-{subset}"
    path = out / "evaluations" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return Evaluation(
        pipeline=pipeline,
        experiment=experiment,
        ground_truth=manifest.annotations,
        iou_threshold=iou,
        coordinate_format=coordinate_format,
        class_source=class_source,
        class_aware=class_aware,
        subset=subset,
        confusion=result["confusion"],
        report=record("file", name, str(path)),
        summary=result["summary"],
        per_class=result["per_class"],
    )


def _evaluation_set(*args, label_mapping=None) -> list[Evaluation]:
    """Class-aware and class-agnostic evaluations over all images, plus the same
    over completed inferences (when some infrastructure failed) and over valid
    responses (when some run did not succeed)."""
    runs = args[4]
    subsets = ["all_images"]
    if any(run.status == "infrastructure_failure" for run in runs):
        subsets.append("completed_inferences")
    if any(run.status != "succeeded" for run in runs):
        subsets.append("valid_responses")
    return [
        _evaluate(
            *args, class_aware=class_aware, subset=subset, label_mapping=label_mapping
        )
        for subset in subsets
        for class_aware in (True, False)
    ]


def _selection(manifest: Manifest, ground_truth: dict) -> tuple[list[str], datetime]:
    selection = json.loads(Path(manifest.selection).read_text(encoding="utf-8"))
    image_ids = [image["image_id"] for image in selection["images"]]
    if sorted(image_ids) != sorted(ground_truth):
        raise ValueError("selection.json and annotations.json list different images.")
    for image in selection["images"]:
        path = Path(manifest.images_dir) / Path(image["image"]).name
        if file_sha256(path) != image["image_sha256"]:
            raise ValueError(f"{path} differs from the selected image (SHA-256).")
    return image_ids, datetime.fromisoformat(selection["created_at"])


def _image(manifest: Manifest, image_id: str) -> ImageReference:
    path = Path(manifest.images_dir) / f"{image_id}.jpg"
    return ImageReference(name=image_id, location=str(path))


def build_report(
    manifest: Manifest,
    manifest_path: Path,
    environment: dict[str, str],
    detector: ObjectDetector | None = None,
    yolo_checks: list[InferenceCheck] | None = None,
) -> ExecutionReportReference:
    """Run the pipelines, evaluate them and save the validated report."""
    missing = [key for key in REQUIRED_CRITERIA if key not in manifest.criteria]
    if missing:
        raise ValueError(f"Pre-registered criteria missing: {missing}")
    out = Path(manifest.output_dir)
    ground_truth = load_ground_truth(Path(manifest.annotations))
    image_ids, selected_at = _selection(manifest, ground_truth)
    inputs = [
        record("file", "manifest", str(manifest_path)),
        record("file", "annotations", manifest.annotations),
        record("file", "selection", manifest.selection),
    ]
    models, pipelines, evaluations = [], [], []

    if manifest.yolo is not None:
        if detector is None or not yolo_checks:
            raise ValueError("The YOLO pipeline needs the detector and its checks.")
        settings = manifest.yolo
        models.append(
            ModelIdentity(
                key="yolo",
                kind="onnx_object_detector",
                name=Path(settings.model_path).name,
                source=settings.model_path,
                revision="sha256:" + file_sha256(Path(settings.model_path)),
                details={
                    "confidence_threshold": str(settings.confidence_threshold),
                    "iou_threshold": str(settings.iou_threshold),
                },
            )
        )
        runs = [
            run_yolo_pipeline(
                _image(manifest, image_id),
                image_id,
                detector,
                "yolo",
                out / "yolo" / image_id,
                yolo_checks,
            )
            for image_id in image_ids
        ]
        pipelines += runs
        evaluations += _evaluation_set(
            "yolo", "detection", "model", "pixel", runs, ground_truth, manifest, out
        )

    if manifest.mirage is not None:
        settings = manifest.mirage
        models.append(
            ModelIdentity(
                key="mirage",
                kind="mirage_official",
                name=settings.model_name,
                source=settings.checkpoint_name,
                revision=settings.checkpoint_revision,
                details={
                    "clip_revision": settings.clip_revision,
                    "official_revision": settings.official_revision,
                },
            )
        )
        expected = MirageExpectations(
            official_revision=settings.official_revision,
            checkpoint_name=settings.checkpoint_name,
            min_gpu_memory_mib=settings.min_gpu_memory_mib,
        )
        for experiment in settings.experiments:
            prompt_file = Path(experiment.prompt_file)
            inputs.append(record("file", f"prompt-{experiment.name}", str(prompt_file)))
            prompt = prompt_file.read_text(encoding="utf-8").strip()
            convert = (
                partial(training_answer_to_json, prompt_class=experiment.prompt_class)
                if experiment.prompt_class
                else None
            )
            runs = []
            for image_id in image_ids:
                run_dir = Path(experiment.runs_dir) / image_id
                _check_run_after_selection(run_dir, selected_at)
                runs.append(
                    run_mirage_pipeline(
                        run_dir,
                        _image(manifest, image_id),
                        image_id,
                        experiment.name,
                        "mirage",
                        experiment.coordinate_format,
                        out / "mirage" / experiment.name.replace(":", "-") / image_id,
                        prompt,
                        expected,
                        convert,
                    )
                )
            pipelines += runs
            truth = ground_truth
            if experiment.prompt_class:
                truth = {
                    image_id: entry
                    | {
                        "objects": [
                            o
                            for o in entry["objects"]
                            if o["cls"] == experiment.prompt_class
                        ]
                    }
                    for image_id, entry in ground_truth.items()
                }
            evaluations += _evaluation_set(
                "mirage",
                experiment.name,
                "prompt" if experiment.prompt_class else "model",
                experiment.coordinate_format,
                runs,
                truth,
                manifest,
                out,
            )

    if manifest.qwen3vl is not None:
        new_models, new_runs, new_evaluations = _qwen3vl(
            manifest, image_ids, selected_at, ground_truth, out
        )
        models += new_models
        pipelines += new_runs
        evaluations += new_evaluations

    report = ExecutionReport(
        run_id=manifest.run_id,
        created_at=datetime.now(UTC),
        environment=environment,
        inputs=inputs,
        criteria=manifest.criteria,
        models=models,
        pipelines=pipelines,
        evaluations=evaluations,
        deviations=manifest.deviations,
    )
    reference = ExecutionReportReference(
        name=manifest.run_id, location=str(out / "report.json")
    )
    ExecutionReportContent(data=report).dematerialize(reference)
    problems = verify_report(reference)
    if problems:
        raise ValueError("Saved report failed verification: " + "; ".join(problems))
    return reference


def _qwen3vl(
    manifest: Manifest,
    image_ids: list[str],
    selected_at: datetime,
    ground_truth: dict[str, dict[str, object]],
    out: Path,
) -> tuple[list[ModelIdentity], list[PipelineRun], list[Evaluation]]:
    """Read the Qwen3-VL runs (one folder per image) and evaluate A and B."""
    settings = manifest.qwen3vl
    model = ModelIdentity(
        key="qwen3vl",
        kind="llamacpp_gguf",
        name=settings.model_name,
        source=", ".join(sorted(settings.files_sha256)),
        revision=settings.revision,
        details={
            "llama_cpp_release": settings.llama_cpp_release,
            "llama_cpp_commit": settings.llama_cpp_commit,
            "config": settings.config,
            "generation": " ".join(settings.generation),
            "coordinates": "relative_1000",
        },
    )
    expected = QwenExpectations(
        files_sha256=settings.files_sha256,
        llama_cpp_commit=settings.llama_cpp_commit,
        config=settings.config,
        generation=tuple(settings.generation),
        min_process_rss_mib=settings.min_process_rss_mib,
    )
    for image_id in image_ids:
        _check_qwen_run_after_selection(Path(settings.runs_dir) / image_id, selected_at)

    def runs_for(
        experiment: str, prompt_name: str, class_source: str
    ) -> list[PipelineRun]:
        return [
            run_qwen_pipeline(
                Path(settings.runs_dir) / image_id,
                prompt_name,
                _image(manifest, image_id),
                image_id,
                experiment,
                "qwen3vl",
                class_source,
                out / "qwen3vl" / experiment.replace(":", "-") / image_id,
                expected,
            )
            for image_id in image_ids
        ]

    experiment, prompt_name = QWEN_JOINT
    joint = runs_for(experiment, prompt_name, "model")
    runs = list(joint)
    evaluations = _evaluation_set(
        "qwen3vl", experiment, "model", "relative_1000", joint, ground_truth,
        manifest, out, label_mapping=settings.label_mapping,
    )  # fmt: skip
    for cls, prompt_name in QWEN_CONDITIONED.items():
        experiment = f"class_conditioned:{cls}"
        conditioned = runs_for(experiment, prompt_name, "prompt")
        runs += conditioned
        truth = {
            image_id: entry
            | {"objects": [o for o in entry["objects"] if o["cls"] == cls]}
            for image_id, entry in ground_truth.items()
        }
        evaluations += _evaluation_set(
            "qwen3vl", experiment, "prompt", "relative_1000", conditioned, truth,
            manifest, out, label_mapping=settings.label_mapping,
        )  # fmt: skip
    return [model], runs, evaluations


def _check_qwen_run_after_selection(run_dir: Path, selected_at: datetime) -> None:
    """Abort if a Qwen run started before the images were selected."""
    run_file = run_dir / "run.json"
    if not run_file.is_file():
        return
    started = json.loads(run_file.read_text(encoding="utf-8")).get("started_at")
    if started is None or datetime.fromisoformat(started) <= selected_at:
        raise ValueError(
            f"{run_dir}: run started before the image selection was recorded; "
            "the selection must be made before any prediction."
        )


def _check_run_after_selection(run_dir: Path, selected_at: datetime) -> None:
    """Abort if a MIRAGE run started before the images were selected."""
    run_file = run_dir / "run.json"
    if not run_file.is_file():
        return
    started = json.loads(run_file.read_text(encoding="utf-8")).get("started_at_utc")
    if started is None or datetime.fromisoformat(started) <= selected_at:
        raise ValueError(
            f"{run_dir}: run started before the image selection was recorded; "
            "the selection must be made before any prediction."
        )


def verify_report(reference: ExecutionReportReference) -> list[str]:
    """Reload the report and check that every recorded file still matches its hash."""
    report = reference.materialize().data
    records = list(report.inputs)
    records += [e.report for e in report.evaluations]
    for run in report.pipelines:
        records += run.inputs + run.outputs + run.evidence
    problems = []
    for item in records:
        path = Path(item.location)
        if not path.is_file():
            problems.append(f"missing {item.location}")
        elif file_sha256(path) != item.sha256:
            problems.append(f"hash mismatch {item.location}")
    return problems


def yolo_inference_checks(
    detector: ObjectDetector, model_path: str
) -> list[InferenceCheck]:
    """Return the checks showing that ``detector`` is the real ONNX model."""
    from mlops_workflows.components.object_detection.detectors.yolo_detector import (
        YoloDetector,
    )

    is_yolo = isinstance(detector, YoloDetector)
    checks = [
        InferenceCheck(
            name="detector_class",
            passed=is_yolo,
            detail=type(detector).__name__,
        )
    ]
    if not is_yolo:
        return checks
    same_file = Path(detector.config.model_path).resolve() == Path(model_path).resolve()
    providers = detector.session.get_providers()
    try:
        check_class_names(detector.class_names)
        classes_ok = True
    except ValueError:
        classes_ok = False
    return [
        *checks,
        InferenceCheck(
            name="model_file",
            passed=same_file,
            detail=f"{detector.config.model_path} (sha256 {file_sha256(Path(model_path))})",
        ),
        InferenceCheck(
            name="onnxruntime_session", passed=bool(providers), detail=str(providers)
        ),
        InferenceCheck(
            name="class_names",
            passed=classes_ok,
            detail=str(list(detector.class_names)),
        ),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = Manifest.model_validate_json(args.manifest.read_text(encoding="utf-8"))

    import cv2
    import numpy
    import onnxruntime

    environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "onnxruntime": onnxruntime.__version__,
        "numpy": numpy.__version__,
        "opencv": cv2.__version__,
    }
    detector, checks = None, None
    if manifest.yolo is not None:
        from mlops_workflows.components.object_detection.detectors.yolo_detector import (
            YoloDetector,
            YoloDetectorConfig,
        )

        detector = YoloDetector(
            YoloDetectorConfig(
                model_path=manifest.yolo.model_path,
                confidence_threshold=manifest.yolo.confidence_threshold,
                iou_threshold=manifest.yolo.iou_threshold,
            )
        )
        checks = yolo_inference_checks(detector, manifest.yolo.model_path)
        failed = [check.name for check in checks if not check.passed]
        if failed:
            print(f"YOLO checks failed: {failed}", file=sys.stderr)
            return 1
    try:
        reference = build_report(manifest, args.manifest, environment, detector, checks)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Report saved and verified: {reference.location}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
