"""Tests for the detection visualization component."""

import numpy as np
import pytest

from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.artifacts.detection.detection_content import DetectionContent
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.artifacts.image.image_content import ImageContent
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.components.detection_visualization.detection_visualization_component import (
    DetectionVisualizationComponent,
)


@pytest.fixture
def artifacts(tmp_path):
    """Create image and detection artifacts for testing."""
    image_reference = ImageReference(
        name="original",
        location=str(tmp_path / "original.png"),
    )

    image = np.zeros((64, 64, 3), dtype=np.uint8)
    ImageContent(data=image).dematerialize(image_reference)

    detection_reference = DetectionReference(
        name="detections",
        location=str(tmp_path / "detections.json"),
    )

    detections = [
        Detection(
            cls="cat",
            conf=0.9,
            box=[10.0, 10.0, 40.0, 40.0],
        )
    ]
    DetectionContent(data=detections).dematerialize(detection_reference)

    return image_reference, detection_reference


def test_prepare_loads_artifacts(tmp_path, artifacts):
    """Load the image and detections."""
    component = DetectionVisualizationComponent(
        output_reference=ImageReference(
            name="output",
            location=str(tmp_path / "output.png"),
        )
    )

    image_content, detection_content = component.prepare(list(artifacts))

    assert isinstance(image_content, ImageContent)
    assert isinstance(detection_content, DetectionContent)
    assert image_content.data.shape == (64, 64, 3)
    assert len(detection_content.data) == 1
    assert detection_content.data[0].cls == "cat"


def test_execute_draws_bounding_box(tmp_path, artifacts):
    """Draw a bounding box and save the annotated image."""
    output_reference = ImageReference(
        name="annotated",
        location=str(tmp_path / "annotated.png"),
    )
    component = DetectionVisualizationComponent(output_reference)

    prepared_data = component.prepare(list(artifacts))
    result = component.execute(prepared_data)

    annotated = output_reference.materialize().data

    assert result == [output_reference]
    assert (tmp_path / "annotated.png").is_file()
    assert annotated[10, 10].tolist() == [0, 255, 0]


def test_original_image_is_preserved(tmp_path, artifacts):
    """Do not modify the original image."""
    output_reference = ImageReference(
        name="annotated",
        location=str(tmp_path / "annotated.png"),
    )
    component = DetectionVisualizationComponent(output_reference)

    image_content, detection_content = component.prepare(list(artifacts))
    original = image_content.data.copy()

    component.execute((image_content, detection_content))

    assert np.array_equal(image_content.data, original)
    assert np.array_equal(artifacts[0].materialize().data, original)


def test_execute_without_detections(tmp_path):
    """Preserve the image when there are no detections."""
    output_reference = ImageReference(
        name="annotated",
        location=str(tmp_path / "annotated.png"),
    )
    component = DetectionVisualizationComponent(output_reference)

    image = np.zeros((64, 64, 3), dtype=np.uint8)
    component.execute((ImageContent(data=image), DetectionContent(data=[])))

    annotated = output_reference.materialize().data

    assert np.array_equal(annotated, image)


def test_prepare_rejects_invalid_artifacts(tmp_path, artifacts):
    """Require the image and detection references in order."""
    component = DetectionVisualizationComponent(
        ImageReference(
            name="output",
            location=str(tmp_path / "output.png"),
        )
    )

    with pytest.raises(ValueError):
        component.prepare([])

    with pytest.raises(ValueError):
        component.prepare([artifacts[0]])

    with pytest.raises(ValueError):
        component.prepare([artifacts[1], artifacts[0]])


def test_execute_rejects_invalid_data(tmp_path):
    """Reject invalid prepared data."""
    component = DetectionVisualizationComponent(
        ImageReference(
            name="output",
            location=str(tmp_path / "output.png"),
        )
    )

    with pytest.raises(TypeError):
        component.execute(None)

    image = np.zeros((64, 64, 3), dtype=np.uint8)
    image_content = ImageContent(data=image)
    detection_content = DetectionContent(data=[])

    with pytest.raises(TypeError):
        component.execute((image_content,))

    with pytest.raises(TypeError):
        component.execute((detection_content, image_content))

    with pytest.raises(TypeError):
        component.execute((image, detection_content))

    with pytest.raises(TypeError):
        component.execute((image_content, []))


def test_execute_draws_detection_without_confidence(tmp_path):
    """Draw boxes whose confidence is unknown, labeled with the class only."""
    image = np.zeros((64, 64, 3), dtype=np.uint8)
    detections = [Detection(cls="WBC", conf=None, box=[10, 10, 40, 40])]

    def render(output_name: str, conf_detections: list[Detection]) -> np.ndarray:
        output_reference = ImageReference(
            name=output_name,
            location=str(tmp_path / f"{output_name}.png"),
        )
        DetectionVisualizationComponent(output_reference).execute(
            (ImageContent(data=image), DetectionContent(data=conf_detections))
        )
        return output_reference.materialize().data

    without_conf = render("without_conf", detections)
    with_conf = render(
        "with_conf",
        [Detection(cls="WBC", conf=0.9, box=[10, 10, 40, 40])],
    )

    assert without_conf[10, 10].tolist() == [0, 255, 0]
    # The label region differs because "0.90" is not drawn.
    assert not np.array_equal(without_conf, with_conf)
