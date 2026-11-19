"""Test ExecutionReportReference loading and round trips."""

import pytest
from pydantic import ValidationError

from mlops_workflows.artifacts.report.execution_report_content import (
    ExecutionReportContent,
)
from mlops_workflows.artifacts.report.execution_report_reference import (
    ExecutionReportReference,
)


def test_report_round_trip(tmp_path, make_report):
    """Persist a report and recover an equal, validated report."""
    reference = ExecutionReportReference(
        name="report", location=str(tmp_path / "e2e" / "report.json")
    )
    content = ExecutionReportContent(data=make_report())

    location = content.dematerialize(reference)
    restored = reference.materialize()

    assert location == reference.location
    assert isinstance(restored, ExecutionReportContent)
    assert restored.data == content.data


def test_annotated_images_are_recovered_by_location(tmp_path, make_report):
    """Image outputs are referenced by location, not embedded."""
    reference = ExecutionReportReference(name="r", location=str(tmp_path / "r.json"))
    ExecutionReportContent(data=make_report()).dematerialize(reference)

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


def test_qwen_pipeline_round_trip(
    tmp_path, make_run, make_report, make_evaluation, yolo_model, qwen_model
):
    qwen_run = make_run(
        pipeline="qwen3vl", experiment="joint_detection", model_key="qwen3vl"
    )
    agnostic = make_evaluation(
        pipeline="qwen3vl",
        experiment="joint_detection",
        coordinate_format="relative_1000",
        class_aware=False,
        subset="valid_responses",
        confusion={"WBC": {"RBC": 1, "WBC": 2}},
    )
    reference = ExecutionReportReference(name="r", location=str(tmp_path / "r.json"))
    content = ExecutionReportContent(
        data=make_report(
            models=[yolo_model, qwen_model],
            pipelines=[make_run(), qwen_run],
            evaluations=[agnostic],
        )
    )

    content.dematerialize(reference)

    assert reference.materialize().data == content.data
