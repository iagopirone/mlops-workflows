"""Unit tests for the pipeline structure validation."""

from dataclasses import FrozenInstanceError

import pytest

from mlops_workflows.pipeline.invalid_pipeline_error import InvalidPipelineError
from mlops_workflows.pipeline.pipeline import Pipeline
from mlops_workflows.pipeline.step import Step


@pytest.fixture
def make_step(component):
    """Build a step with the placeholder component."""

    def build(step_name: str, *depends_on: str) -> Step:
        return Step(step_name=step_name, component=component, depends_on=depends_on)

    return build


def test_accepts_sequential_pipeline(make_step):
    """Accept a chain ending in the finalization."""
    pipeline = Pipeline(
        pipeline_id="sequential",
        steps=(make_step("a"), make_step("b", "a")),
        finalization=make_step("finalize", "b"),
    )

    assert [step.step_name for step in pipeline.all_steps] == [
        "a",
        "b",
        "finalize",
    ]


def test_accepts_parallel_branches_joined_by_finalization(make_step):
    """Accept independent steps that only meet at the finalization."""
    pipeline = Pipeline(
        pipeline_id="parallel",
        steps=(make_step("a"), make_step("b")),
        finalization=make_step("finalize", "a", "b"),
    )

    assert pipeline.finalization.depends_on == ("a", "b")


def test_accepts_path_to_finalization_through_other_steps(make_step):
    """Accept steps that reach the finalization indirectly."""
    pipeline = Pipeline(
        pipeline_id="indirect",
        steps=(make_step("a"), make_step("b", "a"), make_step("c", "a")),
        finalization=make_step("finalize", "b", "c"),
    )

    assert len(pipeline.all_steps) == 4


@pytest.mark.parametrize("pipeline_id", ["", "  "])
def test_rejects_empty_pipeline_id(make_step, pipeline_id):
    """Reject an empty or blank pipeline identifier."""
    with pytest.raises(InvalidPipelineError, match="pipeline id"):
        Pipeline(
            pipeline_id=pipeline_id,
            steps=(make_step("a"),),
            finalization=make_step("finalize", "a"),
        )


def test_rejects_non_string_pipeline_id(make_step):
    """Reject a pipeline identifier that is not text."""
    with pytest.raises(TypeError, match="pipeline_id"):
        Pipeline(
            pipeline_id=1,
            steps=(make_step("a"),),
            finalization=make_step("finalize", "a"),
        )


def test_rejects_pipeline_without_processing_steps(make_step):
    """Reject a pipeline that only has the finalization."""
    with pytest.raises(InvalidPipelineError, match="at least one processing"):
        Pipeline(
            pipeline_id="empty",
            steps=(),
            finalization=make_step("finalize"),
        )


def test_rejects_duplicated_processing_step_names(make_step):
    """Reject two processing steps with the same identifier."""
    with pytest.raises(InvalidPipelineError, match="Duplicated step names: a"):
        Pipeline(
            pipeline_id="duplicated",
            steps=(make_step("a"), make_step("a")),
            finalization=make_step("finalize", "a"),
        )


def test_rejects_finalization_name_used_by_processing_step(make_step):
    """Reject a processing step that shares the finalization identifier."""
    with pytest.raises(InvalidPipelineError, match="Duplicated step names: done"):
        Pipeline(
            pipeline_id="duplicated",
            steps=(make_step("done"),),
            finalization=make_step("done"),
        )


def test_rejects_dependency_outside_the_pipeline(make_step):
    """Reject a dependency on a step that the pipeline does not define."""
    with pytest.raises(
        InvalidPipelineError,
        match="outside the pipeline: b -> missing",
    ):
        Pipeline(
            pipeline_id="external",
            steps=(make_step("a"), make_step("b", "missing")),
            finalization=make_step("finalize", "a", "b"),
        )


def test_rejects_finalization_dependency_outside_the_pipeline(make_step):
    """Reject a finalization prerequisite that the pipeline does not define."""
    with pytest.raises(
        InvalidPipelineError,
        match="outside the pipeline: finalize -> missing",
    ):
        Pipeline(
            pipeline_id="external",
            steps=(make_step("a"),),
            finalization=make_step("finalize", "a", "missing"),
        )


def test_rejects_two_step_cycle(make_step):
    """Reject steps that depend on each other."""
    with pytest.raises(InvalidPipelineError, match="Circular dependency: a -> b -> a"):
        Pipeline(
            pipeline_id="cycle",
            steps=(make_step("a", "b"), make_step("b", "a")),
            finalization=make_step("finalize", "a", "b"),
        )


def test_rejects_longer_cycle(make_step):
    """Reject a cycle that goes through three steps."""
    with pytest.raises(
        InvalidPipelineError,
        match="Circular dependency: a -> c -> b -> a",
    ):
        Pipeline(
            pipeline_id="cycle",
            steps=(
                make_step("a", "c"),
                make_step("b", "a"),
                make_step("c", "b"),
            ),
            finalization=make_step("finalize", "c"),
        )


def test_rejects_step_depending_on_finalization(make_step):
    """Reject the finalization as a prerequisite of another step."""
    with pytest.raises(
        InvalidPipelineError,
        match="depending on the finalization: b",
    ):
        Pipeline(
            pipeline_id="after-finalization",
            steps=(make_step("a"), make_step("b", "finalize")),
            finalization=make_step("finalize", "a"),
        )


def test_rejects_step_without_path_to_finalization(make_step):
    """Reject a branch whose result the finalization never waits for."""
    with pytest.raises(
        InvalidPipelineError,
        match="without a path to the finalization: c",
    ):
        Pipeline(
            pipeline_id="dangling",
            steps=(make_step("a"), make_step("b", "a"), make_step("c", "a")),
            finalization=make_step("finalize", "b"),
        )


def test_rejects_finalization_without_prerequisites(make_step):
    """Reject a finalization that could start before any processing step."""
    with pytest.raises(
        InvalidPipelineError,
        match="without a path to the finalization: a",
    ):
        Pipeline(
            pipeline_id="early",
            steps=(make_step("a"),),
            finalization=make_step("finalize"),
        )


def test_rejects_list_of_steps(make_step):
    """Reject a mutable collection of steps."""
    with pytest.raises(TypeError, match="tuple of steps"):
        Pipeline(
            pipeline_id="mutable",
            steps=[make_step("a")],
            finalization=make_step("finalize", "a"),
        )


def test_rejects_items_that_are_not_steps(make_step):
    """Reject processing steps or finalization of another type."""
    with pytest.raises(TypeError, match="Step instances"):
        Pipeline(
            pipeline_id="wrong-type",
            steps=(make_step("a"),),
            finalization="finalize",
        )


def test_pipeline_is_immutable(make_step):
    """Reject changes after the structure was validated."""
    pipeline = Pipeline(
        pipeline_id="frozen",
        steps=(make_step("a"),),
        finalization=make_step("finalize", "a"),
    )

    with pytest.raises(FrozenInstanceError):
        pipeline.steps = ()
