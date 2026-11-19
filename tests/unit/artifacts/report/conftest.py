"""Provide example execution report data shared by the report tests.

The builders return valid objects by default. Each test passes only the
fields it changes, so the intent of the test stays visible at the call site.
"""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import pytest

from mlops_workflows.artifacts.report.execution_report import (
    ArtifactRecord,
    Evaluation,
    ExecutionReport,
    InferenceCheck,
    ModelIdentity,
    PipelineRun,
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


QWEN = ModelIdentity(
    key="qwen3vl",
    kind="llamacpp_gguf",
    name="Qwen/Qwen3-VL-2B-Instruct-GGUF Q4_K_M",
    source="experiments/qwen3vl/models/Qwen3VL-2B-Instruct-Q4_K_M.gguf",
    revision="52d6c8ffea26cc873ac5ad116f8631268d7eb503",
    details={"llama_cpp_commit": "6f1e6543704bc5b080c7a98e7b6f707b31f6ed51"},
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


@pytest.fixture
def sha256() -> str:
    """Provide a valid SHA-256 hex digest."""
    return HASH


@pytest.fixture
def yolo_model() -> ModelIdentity:
    """Provide the identity of a real ONNX detector."""
    return YOLO


@pytest.fixture
def qwen_model() -> ModelIdentity:
    """Provide the identity of a real llama.cpp GGUF model."""
    return QWEN


@pytest.fixture
def passed_checks() -> list[InferenceCheck]:
    """Provide real-inference checks that all passed."""
    return PASSED


@pytest.fixture
def make_run() -> Callable[..., PipelineRun]:
    """Build a valid YOLO pipeline run, overriding the given fields."""
    return run


@pytest.fixture
def make_evaluation() -> Callable[..., Evaluation]:
    """Build a valid YOLO evaluation, overriding the given fields."""
    return evaluation


@pytest.fixture
def make_report() -> Callable[..., ExecutionReport]:
    """Build a valid report with YOLO and MIRAGE, overriding the given fields."""
    return report
