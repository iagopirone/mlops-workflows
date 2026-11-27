"""Define a processing step of a pipeline."""

from dataclasses import dataclass

from mlops_workflows.artifacts.interface import ArtifactReference
from mlops_workflows.components.interface import Component
from mlops_workflows.pipeline.invalid_pipeline_error import InvalidPipelineError


@dataclass(frozen=True)
class Step:
    """Represent the use of a component inside a pipeline.

    ``step_name`` identifies the step within its pipeline. ``depends_on``
    holds the identifiers of the steps that must complete before this one
    starts. The structure is immutable because the same definition is
    shared by every execution of the pipeline; the component and artifact
    references it holds are not frozen.
    """

    step_name: str
    component: Component
    depends_on: tuple[str, ...] = ()
    input_artifacts: tuple[ArtifactReference, ...] = ()
    output_artifacts: tuple[ArtifactReference, ...] = ()

    def __post_init__(self) -> None:
        """Reject inconsistencies that depend only on this step."""
        for field_name in ("depends_on", "input_artifacts", "output_artifacts"):
            if not isinstance(getattr(self, field_name), tuple):
                raise TypeError(f"Expected a tuple for {field_name}.")

        if not isinstance(self.component, Component):
            raise TypeError("Expected a Component instance for component.")

        for field_name in ("input_artifacts", "output_artifacts"):
            if not all(
                isinstance(artifact, ArtifactReference)
                for artifact in getattr(self, field_name)
            ):
                raise TypeError(f"Expected ArtifactReference items in {field_name}.")

        if not isinstance(self.step_name, str):
            raise TypeError("Expected a string step_name.")

        if not self.step_name.strip():
            raise InvalidPipelineError("The step name must not be empty.")

        if not all(isinstance(name, str) for name in self.depends_on):
            raise TypeError("Expected step names in depends_on.")

        if self.step_name in self.depends_on:
            raise InvalidPipelineError(f"Step '{self.step_name}' depends on itself.")

        if len(set(self.depends_on)) != len(self.depends_on):
            raise InvalidPipelineError(
                f"Step '{self.step_name}' lists a dependency more than once."
            )
