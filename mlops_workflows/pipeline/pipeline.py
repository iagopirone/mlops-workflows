"""Define a pipeline and validate the structure of its steps."""

from collections import Counter
from dataclasses import dataclass

from mlops_workflows.pipeline.invalid_pipeline_error import InvalidPipelineError
from mlops_workflows.pipeline.step import Step


@dataclass(frozen=True)
class Pipeline:
    """Group the processing steps and the finalization of a workflow.

    The finalization is a regular step kept in its own field, so every
    pipeline has exactly one. The structure is validated on creation: an
    invalid pipeline cannot be built.
    """

    pipeline_id: str
    steps: tuple[Step, ...]
    finalization: Step

    def __post_init__(self) -> None:
        """Reject inconsistent pipeline structures."""
        if not isinstance(self.steps, tuple):
            raise TypeError("Expected a tuple of steps.")

        if not all(isinstance(step, Step) for step in self.all_steps):
            raise TypeError("Expected Step instances.")

        if not isinstance(self.pipeline_id, str):
            raise TypeError("Expected a string pipeline_id.")

        if not self.pipeline_id.strip():
            raise InvalidPipelineError("The pipeline id must not be empty.")

        if not self.steps:
            raise InvalidPipelineError(
                "The pipeline needs at least one processing step."
            )

        self._reject_duplicate_names()
        self._reject_unknown_dependencies()
        self._reject_dependencies_on_finalization()
        self._reject_cycles()
        self._reject_steps_outside_finalization()

    @property
    def all_steps(self) -> tuple[Step, ...]:
        """Return the processing steps followed by the finalization."""
        return (*self.steps, self.finalization)

    def _dependencies(self) -> dict[str, tuple[str, ...]]:
        return {step.step_name: step.depends_on for step in self.all_steps}

    def _reject_duplicate_names(self) -> None:
        counts = Counter(step.step_name for step in self.all_steps)
        duplicated = [name for name, count in counts.items() if count > 1]

        if duplicated:
            raise InvalidPipelineError(
                f"Duplicated step names: {', '.join(duplicated)}."
            )

    def _reject_unknown_dependencies(self) -> None:
        names = {step.step_name for step in self.all_steps}
        unknown = [
            f"{step.step_name} -> {dependency}"
            for step in self.all_steps
            for dependency in step.depends_on
            if dependency not in names
        ]

        if unknown:
            raise InvalidPipelineError(
                f"Dependencies outside the pipeline: {', '.join(unknown)}."
            )

    def _reject_dependencies_on_finalization(self) -> None:
        dependents = [
            step.step_name
            for step in self.steps
            if self.finalization.step_name in step.depends_on
        ]

        if dependents:
            raise InvalidPipelineError(
                f"Steps depending on the finalization: {', '.join(dependents)}."
            )

    def _reject_cycles(self) -> None:
        dependencies = self._dependencies()
        completed: set[str] = set()

        def find_cycle(name: str, path: list[str]) -> list[str] | None:
            if name in path:
                return [*path[path.index(name) :], name]
            if name in completed:
                return None

            for dependency in dependencies[name]:
                cycle = find_cycle(dependency, [*path, name])
                if cycle:
                    return cycle

            completed.add(name)
            return None

        for name in dependencies:
            cycle = find_cycle(name, [])
            if cycle:
                raise InvalidPipelineError(
                    f"Circular dependency: {' -> '.join(cycle)}."
                )

    def _reject_steps_outside_finalization(self) -> None:
        dependencies = self._dependencies()
        reached: set[str] = set()
        pending = list(self.finalization.depends_on)

        while pending:
            name = pending.pop()
            if name not in reached:
                reached.add(name)
                pending.extend(dependencies[name])

        unreached = [
            step.step_name for step in self.steps if step.step_name not in reached
        ]

        if unreached:
            raise InvalidPipelineError(
                f"Steps without a path to the finalization: {', '.join(unreached)}."
            )
