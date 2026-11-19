"""Define the structure of an end-to-end execution report."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

NonEmpty = Annotated[str, Field(min_length=1)]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ReportModel(BaseModel):
    """Base for report parts: strict and without unknown fields."""

    model_config = ConfigDict(strict=True, extra="forbid")


class ModelIdentity(ReportModel):
    """Identify one real model used in the execution.

    ``revision`` is a file SHA-256 or a model/code revision. Only real model
    kinds exist, so a simulated answerer cannot be recorded as a model.
    """

    key: NonEmpty
    kind: Literal["onnx_object_detector", "mirage_official", "llamacpp_gguf"]
    name: NonEmpty
    source: NonEmpty
    revision: NonEmpty
    details: dict[str, str] = Field(default_factory=dict)


class ArtifactRecord(ReportModel):
    """Point to a file read or written by a pipeline, with its SHA-256."""

    kind: Literal["image", "text", "detection", "file"]
    name: NonEmpty
    location: NonEmpty
    sha256: Sha256


class InferenceCheck(ReportModel):
    """One piece of evidence that a real model inference happened.

    A model identifier in metadata is not enough on its own; checks such as the
    official output markers, the code and checkpoint revisions, offline mode and
    the GPU memory used during the run are recorded one by one.
    """

    name: NonEmpty
    passed: bool
    detail: NonEmpty


class PipelineRun(ReportModel):
    """Record one pipeline execution on one image.

    Statuses keep three kinds of problems apart: ``infrastructure_failure``
    (the model did not run or its output could not be read), ``invalid_response``
    (the model answered, but the answer is not a valid detection list) and
    ``succeeded`` (detections were produced; whether they are correct is
    measured by the evaluation, not here).
    """

    pipeline: Literal["yolo", "mirage", "qwen3vl"]
    experiment: NonEmpty
    model_key: NonEmpty
    image_id: NonEmpty
    status: Literal["succeeded", "invalid_response", "infrastructure_failure"]
    class_source: Literal["model", "prompt"]
    error: str | None
    detection_count: Annotated[int, Field(ge=0)] | None
    duration_seconds: Annotated[float, Field(ge=0)] | None
    inputs: list[ArtifactRecord]
    outputs: list[ArtifactRecord]
    evidence: list[ArtifactRecord]
    inference_checks: list[InferenceCheck]

    @model_validator(mode="after")
    def check_status(self) -> "PipelineRun":
        """Require an error for failures and a detection count for successes.

        A model answer (``succeeded`` or ``invalid_response``) is only accepted
        when every real-inference check is present and passed.
        """
        if self.status != "infrastructure_failure" and (
            not self.inference_checks
            or not all(check.passed for check in self.inference_checks)
        ):
            raise ValueError(
                "A model answer needs passed real-inference checks; otherwise "
                "record an infrastructure_failure."
            )
        if self.status == "succeeded":
            if self.error is not None or self.detection_count is None:
                raise ValueError(
                    "A succeeded run needs a detection count and no error."
                )
        elif not self.error or self.detection_count is not None:
            raise ValueError(
                "A failed or invalid run needs an error and no detection count."
            )
        return self


class Evaluation(ReportModel):
    """Summarize the comparison of one pipeline with human annotations."""

    pipeline: Literal["yolo", "mirage", "qwen3vl"]
    experiment: NonEmpty
    ground_truth: NonEmpty
    iou_threshold: Annotated[float, Field(gt=0, le=1)]
    coordinate_format: NonEmpty
    class_source: Literal["model", "prompt"]
    # False: boxes matched regardless of class (localization alone).
    class_aware: bool = True
    # Reported next to, never instead of, "all_images":
    # "completed_inferences" drops only infrastructure failures (invalid
    # outputs stay as model failures with zero detections);
    # "valid_responses" keeps only images whose run produced a valid answer.
    subset: Literal["all_images", "completed_inferences", "valid_responses"] = (
        "all_images"
    )
    # Annotated class -> predicted class -> matched pairs.
    confusion: dict[str, dict[str, int]] = Field(default_factory=dict)
    report: ArtifactRecord
    summary: dict[str, int | float | None]
    per_class: dict[str, dict[str, int | float | None]]


class ExecutionReport(ReportModel):
    """Collect models, runs, evaluations and deviations of one execution."""

    run_id: NonEmpty
    created_at: datetime
    environment: dict[str, str]
    inputs: list[ArtifactRecord]
    criteria: dict[str, float]
    models: list[ModelIdentity] = Field(min_length=1)
    pipelines: list[PipelineRun]
    evaluations: list[Evaluation]
    deviations: list[str]

    @field_validator("created_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Reject timestamps without a timezone."""
        if value.tzinfo is None:
            raise ValueError("created_at must include a timezone.")
        return value

    @model_validator(mode="after")
    def check_models(self) -> "ExecutionReport":
        """Require unique model keys that match each pipeline's model kind."""
        kinds = {model.key: model.kind for model in self.models}
        if len(kinds) != len(self.models):
            raise ValueError("Model keys must be unique.")
        expected = {
            "yolo": "onnx_object_detector",
            "mirage": "mirage_official",
            "qwen3vl": "llamacpp_gguf",
        }
        for run in self.pipelines:
            if run.model_key not in kinds:
                raise ValueError(f"Unknown model key: {run.model_key!r}")
            if kinds[run.model_key] != expected[run.pipeline]:
                raise ValueError(
                    f"Pipeline {run.pipeline!r} cannot use a "
                    f"{kinds[run.model_key]!r} model."
                )
        return self
