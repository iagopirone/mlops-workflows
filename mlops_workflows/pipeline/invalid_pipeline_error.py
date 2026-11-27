"""Define the error raised for inconsistent pipeline definitions."""


class InvalidPipelineError(ValueError):
    """Signal that a step or pipeline definition is structurally invalid."""
