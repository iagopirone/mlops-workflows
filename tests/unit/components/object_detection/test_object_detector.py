"""Test the object detector interface."""

import pytest

from mlops_workflows.components.object_detection.object_detector import ObjectDetector


def test_object_detector_cannot_be_instantiated():
    """Ensure the abstract detector cannot be instantiated."""
    with pytest.raises(TypeError):
        ObjectDetector()
