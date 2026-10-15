from mlops_workflows.domain import Artifact, Component, Step


class ExampleComponent(Component):
    def prepare(self, input_artifacts: list[Artifact]) -> object:
        return input_artifacts

    def execute(self, prepared_data: object) -> list[Artifact]:
        return []


def test_steps_have_independent_lists():
    component = ExampleComponent()
    first = Step(step_name="first", component=component)
    second = Step(step_name="second", component=component)

    second.depends_on.append(first)

    assert first.depends_on == []
    assert second.depends_on == [first]
    assert first.input_artifacts is not second.input_artifacts
    assert first.output_artifacts is not second.output_artifacts
