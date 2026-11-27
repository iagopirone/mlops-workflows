"""Unit tests for the pipeline step definition."""

from dataclasses import FrozenInstanceError

import pytest

from mlops_workflows.artifacts.text.text_reference import TextReference
from mlops_workflows.pipeline.invalid_pipeline_error import InvalidPipelineError
from mlops_workflows.pipeline.step import Step


def test_valid_step_keeps_its_fields(component):
    """Keep the identifier, component, dependencies, and artifacts."""
    prompt = TextReference(name="prompt", location="prompt.txt")
    answer = TextReference(name="answer", location="answer.txt")

    step = Step(
        step_name="answer",
        component=component,
        depends_on=("load", "resize"),
        input_artifacts=(prompt,),
        output_artifacts=(answer,),
    )

    assert step.step_name == "answer"
    assert step.component is component
    assert step.depends_on == ("load", "resize")
    assert step.input_artifacts == (prompt,)
    assert step.output_artifacts == (answer,)


def test_step_defaults_to_no_dependencies_or_artifacts(component):
    """Accept a step without dependencies or artifacts."""
    step = Step(step_name="load", component=component)

    assert step.depends_on == ()
    assert step.input_artifacts == ()
    assert step.output_artifacts == ()


@pytest.mark.parametrize("step_name", ["", "   "])
def test_rejects_empty_step_name(component, step_name):
    """Reject an empty or blank identifier."""
    with pytest.raises(InvalidPipelineError, match="must not be empty"):
        Step(step_name=step_name, component=component)


def test_rejects_non_string_step_name(component):
    """Reject an identifier that is not text."""
    with pytest.raises(TypeError, match="step_name"):
        Step(step_name=1, component=component)


def test_rejects_self_dependency(component):
    """Reject a step that depends on itself."""
    with pytest.raises(InvalidPipelineError, match="depends on itself"):
        Step(step_name="count", component=component, depends_on=("count",))


def test_rejects_repeated_dependency(component):
    """Reject the same dependency listed twice."""
    with pytest.raises(InvalidPipelineError, match="more than once"):
        Step(
            step_name="count",
            component=component,
            depends_on=("detect", "detect"),
        )


@pytest.mark.parametrize(
    "field_name",
    ["depends_on", "input_artifacts", "output_artifacts"],
)
def test_rejects_lists_instead_of_tuples(component, field_name):
    """Reject mutable collections, which would make the step mutable."""
    with pytest.raises(TypeError, match=field_name):
        Step(step_name="count", component=component, **{field_name: []})


def test_rejects_non_string_dependency(component):
    """Reject dependencies that are not step identifiers."""
    other = Step(step_name="detect", component=component)

    with pytest.raises(TypeError, match="step names"):
        Step(step_name="count", component=component, depends_on=(other,))


def test_rejects_component_that_is_not_a_component():
    """Reject an object that does not implement the Component contract."""
    with pytest.raises(TypeError, match="Component instance"):
        Step(step_name="count", component=object())


@pytest.mark.parametrize("field_name", ["input_artifacts", "output_artifacts"])
def test_rejects_items_that_are_not_artifact_references(component, field_name):
    """Reject artifacts given as plain locations instead of references."""
    with pytest.raises(TypeError, match=f"ArtifactReference items in {field_name}"):
        Step(
            step_name="count",
            component=component,
            **{field_name: ("detections.json",)},
        )


def test_rejects_non_reference_mixed_with_references(component):
    """Reject a tuple where only some items are artifact references."""
    detections = TextReference(name="detections", location="detections.txt")

    with pytest.raises(TypeError, match="input_artifacts"):
        Step(
            step_name="count",
            component=component,
            input_artifacts=(detections, None),
        )


def test_step_is_immutable(component):
    """Reject changes after creation."""
    step = Step(step_name="count", component=component)

    with pytest.raises(FrozenInstanceError):
        step.depends_on = ("detect",)
