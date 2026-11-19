"""Test ExecutionReportReference loading and round trips."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from mlops_workflows.artifacts.report.execution_report import (
    ArtifactRecord,
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

HASH = "a" * 64


YOLO = ModelIdentity(
    key="yolo",
    kind="onnx_object_detector",
    name="best.onnx",
    source="/models/best.onnx",
    revision="sha256:" + "0" * 64,
    details={"confidence_threshold": "0.25"},
)


MIRAGE = ModelIdentity(
    key="mirage",
    kind="mirage_official",
    name="tsunghanwu/mirage-llama3.1-8.3B",
    source="/ckpt/mirage-llama3.1-8.3B",
    revision="100ea29f5fb9dbd35d52390075abd9f60b225478",
)


PASSED = [InferenceCheck(name="gpu_memory_loaded", passed=True, detail="20100 MiB")]


def record(kind="image", name="image", location="in.jpg") -> ArtifactRecord:
    return ArtifactRecord(kind=kind, name=name, location=location, sha256=HASH)


def run(**changes) -> PipelineRun:
    values = {
        "pipeline": "yolo",
        "experiment": "detection",
        "model_key": "yolo",
        "image_id": "BloodImage_00001",
        "status": "succeeded",
        "class_source": "model",
        "error": None,
        "detection_count": 3,
        "duration_seconds": 0.5,
        "inputs": [record()],
        "outputs": [
            record("detection", "detections", "d.json"),
            record("image", "annotated", "a.png"),
        ],
        "evidence": [],
        "inference_checks": PASSED,
    }
    values.update(changes)
    return PipelineRun(**values)


def evaluation(**changes) -> Evaluation:
    values = {
        "pipeline": "yolo",
        "experiment": "detection",
        "ground_truth": "annotations.json",
        "iou_threshold": 0.5,
        "coordinate_format": "pixel",
        "class_source": "model",
        "report": record("file", "yolo-eval", "yolo-eval.json"),
        "summary": {"true_positives": 1, "precision": 0.5, "recall": None},
        "per_class": {"WBC": {"true_positives": 1, "precision": 1.0}},
    }
    values.update(changes)
    return Evaluation(**values)


def report(**changes) -> ExecutionReport:
    values = {
        "run_id": "2026-11-18-e2e",
        "created_at": datetime(
            2026, 11, 18, 15, 0, tzinfo=timezone(timedelta(hours=-3))
        ),
        "environment": {"python": "3.12.14"},
        "inputs": [record("file", "annotations", "annotations.json")],
        "criteria": {"iou_threshold": 0.5, "min_valid_response_rate": 0.8},
        "models": [YOLO, MIRAGE],
        "pipelines": [
            run(),
            run(
                pipeline="mirage",
                experiment="json_prompt",
                model_key="mirage",
                status="invalid_response",
                error="The response is not valid JSON",
                detection_count=None,
                outputs=[],
                evidence=[record("file", "run", "run.json")],
            ),
        ],
        "evaluations": [evaluation()],
        "deviations": ["torchvision 0.16.2 instead of 0.15.2"],
    }
    values.update(changes)
    return ExecutionReport(**values)


QWEN = ModelIdentity(
    key="qwen3vl",
    kind="llamacpp_gguf",
    name="Qwen/Qwen3-VL-2B-Instruct-GGUF Q4_K_M",
    source="experiments/qwen3vl/models/Qwen3VL-2B-Instruct-Q4_K_M.gguf",
    revision="52d6c8ffea26cc873ac5ad116f8631268d7eb503",
    details={"llama_cpp_commit": "6f1e6543704bc5b080c7a98e7b6f707b31f6ed51"},
)


def test_report_round_trip(tmp_path):
    """Persist a report and recover an equal, validated report."""
    reference = ExecutionReportReference(
        name="report", location=str(tmp_path / "e2e" / "report.json")
    )
    content = ExecutionReportContent(data=report())

    location = content.dematerialize(reference)
    restored = reference.materialize()

    assert location == reference.location
    assert isinstance(restored, ExecutionReportContent)
    assert restored.data == content.data


def test_annotated_images_are_recovered_by_location(tmp_path):
    """Image outputs are referenced by location, not embedded."""
    reference = ExecutionReportReference(name="r", location=str(tmp_path / "r.json"))
    ExecutionReportContent(data=report()).dematerialize(reference)

    restored = reference.materialize().data
    images = [
        item.location
        for pipeline_run in restored.pipelines
        for item in pipeline_run.outputs
        if item.kind == "image"
    ]

    assert images == ["a.png"]


def test_missing_report_file(tmp_path):
    reference = ExecutionReportReference(name="r", location=str(tmp_path / "no.json"))

    with pytest.raises(FileNotFoundError):
        reference.materialize()


def test_corrupted_report_file_is_rejected(tmp_path):
    path = tmp_path / "r.json"
    path.write_text('{"run_id": "x"}', encoding="utf-8")

    with pytest.raises(ValidationError):
        ExecutionReportReference(name="r", location=str(path)).materialize()


def test_qwen_pipeline_round_trip(tmp_path):
    qwen_run = run(
        pipeline="qwen3vl", experiment="joint_detection", model_key="qwen3vl"
    )
    agnostic = evaluation(
        pipeline="qwen3vl",
        experiment="joint_detection",
        coordinate_format="relative_1000",
        class_aware=False,
        subset="valid_responses",
        confusion={"WBC": {"RBC": 1, "WBC": 2}},
    )
    reference = ExecutionReportReference(name="r", location=str(tmp_path / "r.json"))
    content = ExecutionReportContent(
        data=report(
            models=[YOLO, QWEN], pipelines=[run(), qwen_run], evaluations=[agnostic]
        )
    )

    content.dematerialize(reference)

    assert reference.materialize().data == content.data
