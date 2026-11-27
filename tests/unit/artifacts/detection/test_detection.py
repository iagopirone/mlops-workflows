"""Test the Detection model."""

import pytest
from pydantic import ValidationError

from mlops_workflows.artifacts.detection.detection import Detection


def test_detection_requires_explicit_confidence():
    """Require conf to be given, even when it is None."""
    with pytest.raises(ValidationError):
        Detection(cls="WBC", box=[1, 2, 3, 4])


@pytest.mark.parametrize("conf", [-0.01, 1.01])
def test_detection_rejects_confidence_out_of_range(conf):
    """Keep validating numeric confidence values."""
    with pytest.raises(ValidationError):
        Detection(cls="WBC", conf=conf, box=[1, 2, 3, 4])
