"""Test the ExecutionReport model and its validation rules."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from mlops_workflows.artifacts.report.execution_report import (
    ArtifactRecord,
    InferenceCheck,
    ModelIdentity,
    PipelineRun,
)


def test_report_requires_at_least_one_model(make_report):
    with pytest.raises(ValidationError, match="at least 1"):
        make_report(models=[], pipelines=[])


def test_simulated_model_kind_is_rejected():
    with pytest.raises(ValidationError):
        ModelIdentity(
            key="fake",
            kind="fake_answerer",
            name="FakeAnswerer",
            source="tests",
            revision="none",
        )


@pytest.mark.parametrize("field", ["key", "name", "source", "revision"])
def test_model_identity_fields_must_not_be_empty(field, yolo_model):
    values = yolo_model.model_dump() | {field: ""}

    with pytest.raises(ValidationError):
        ModelIdentity(**values)


@pytest.mark.parametrize("value", ["", "abc", "A" * 64, "g" * 64])
def test_records_need_a_sha256(value):
    with pytest.raises(ValidationError):
        ArtifactRecord(kind="file", name="x", location="x", sha256=value)


def test_model_answer_needs_inference_checks(make_run):
    with pytest.raises(ValidationError, match="real-inference checks"):
        make_run(inference_checks=[])


@pytest.mark.parametrize("status", ["succeeded", "invalid_response"])
def test_model_answer_needs_all_checks_passed(status, make_run, passed_checks):
    failed = [
        *passed_checks,
        InferenceCheck(name="official_code_revision", passed=False, detail="dirty"),
    ]
    extra = {} if status == "succeeded" else {"error": "x", "detection_count": None}

    with pytest.raises(ValidationError, match="real-inference checks"):
        make_run(status=status, inference_checks=failed, **extra)


def test_infrastructure_failure_may_have_failed_checks(make_run):
    failed = [InferenceCheck(name="gpu_memory_loaded", passed=False, detail="none")]

    result = make_run(
        status="infrastructure_failure",
        error="Insufficient evidence of real inference",
        detection_count=None,
        inference_checks=failed,
    )

    assert result.inference_checks[0].passed is False


def test_class_source_is_required(make_run):
    values = make_run().model_dump(exclude={"class_source"})

    with pytest.raises(ValidationError):
        PipelineRun(**values)


def test_pipeline_must_use_a_known_model(make_run, make_report):
    with pytest.raises(ValidationError, match="Unknown model key"):
        make_report(pipelines=[make_run(model_key="other")])


def test_pipeline_must_use_a_model_of_its_kind(make_run, make_report):
    with pytest.raises(ValidationError, match="cannot use"):
        make_report(pipelines=[make_run(pipeline="mirage", model_key="yolo")])


def test_model_keys_must_be_unique(make_report, yolo_model):
    with pytest.raises(ValidationError, match="unique"):
        make_report(models=[yolo_model, yolo_model])


def test_created_at_needs_timezone(make_report):
    with pytest.raises(ValidationError, match="timezone"):
        make_report(created_at=datetime(2026, 11, 18, 15, 0))


def test_utc_timestamp_is_accepted(make_report):
    assert make_report(created_at=datetime(2026, 11, 18, tzinfo=UTC)).created_at.tzinfo


@pytest.mark.parametrize(
    "changes",
    [
        {"error": "boom"},
        {"detection_count": None},
        {"status": "invalid_response"},
        {"status": "infrastructure_failure", "error": "OOM", "detection_count": 2},
        {"status": "infrastructure_failure", "error": "", "detection_count": None},
    ],
)
def test_status_consistency(changes, make_run):
    with pytest.raises(ValidationError):
        make_run(**changes)


def test_failure_statuses_are_distinct(make_run):
    infra = make_run(
        status="infrastructure_failure",
        error="CUDA out of memory",
        detection_count=None,
    )
    invalid = make_run(
        status="invalid_response", error="not JSON", detection_count=None
    )

    assert {infra.status, invalid.status} == {
        "infrastructure_failure",
        "invalid_response",
    }


def test_extra_fields_are_rejected(sha256):
    with pytest.raises(ValidationError):
        ArtifactRecord(kind="image", name="a", location="a.png", sha256=sha256, x=1)


@pytest.mark.parametrize("threshold", [0, 1.5])
def test_iou_threshold_range(threshold, make_evaluation):
    with pytest.raises(ValidationError):
        make_evaluation(iou_threshold=threshold)


def test_qwen_pipeline_needs_a_llamacpp_model(
    make_run, make_report, yolo_model, qwen_model
):
    with pytest.raises(ValidationError, match="cannot use"):
        make_report(
            models=[yolo_model, qwen_model],
            pipelines=[make_run(pipeline="qwen3vl", model_key="yolo")],
        )


def test_qwen_answer_still_needs_inference_checks(make_run):
    with pytest.raises(ValidationError, match="real-inference checks"):
        make_run(pipeline="qwen3vl", model_key="qwen3vl", inference_checks=[])


def test_evaluation_defaults_keep_previous_reports_valid(make_evaluation):
    result = make_evaluation()

    assert (result.class_aware, result.subset, result.confusion) == (
        True,
        "all_images",
        {},
    )


def test_evaluation_rejects_unknown_subset(make_evaluation):
    with pytest.raises(ValidationError):
        make_evaluation(subset="best_images")


def test_completed_inferences_subset_is_accepted(make_evaluation):
    assert (
        make_evaluation(subset="completed_inferences").subset == "completed_inferences"
    )
