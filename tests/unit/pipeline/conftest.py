"""Provide a minimal component for the pipeline structure tests.

Pipeline validation never runs the components, so the tests use a
placeholder that only fills the ``component`` field of each step.
"""

import pytest

from mlops_workflows.artifacts.interface import ArtifactReference
from mlops_workflows.components.interface import Component


class PlaceholderComponent(Component):
    """Fill a step without implementing any processing."""

    def prepare(self, input_artifacts: list[ArtifactReference]) -> object:
        raise NotImplementedError

    def execute(self, prepared_data: object) -> list[ArtifactReference]:
        raise NotImplementedError


@pytest.fixture
def component() -> Component:
    """Return a component that is never executed."""
    return PlaceholderComponent()
