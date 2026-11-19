"""Test the text detection parsing component."""

import json
from pathlib import Path

import numpy as np
import pytest

from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.artifacts.detection.detection_content import DetectionContent
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.artifacts.image.image_content import ImageContent
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.artifacts.text.text_content import TextContent
from mlops_workflows.artifacts.text.text_reference import TextReference
from mlops_workflows.components.text_detection_parsing.text_detection_parser import (
    TextDetectionParser,
)
from mlops_workflows.components.text_detection_parsing.text_detection_parsing_component import (
    TextDetectionParsingComponent,
)

RESPONSE = '[{"cls": "WBC", "box": [0.1, 0.35, 0.5, 0.65]}]'


@pytest.fixture
def image() -> np.ndarray:
    """Provide a landscape BGR image (width 100, height 50)."""
    return np.zeros((50, 100, 3), dtype=np.uint8)


@pytest.fixture
def artifacts(tmp_path, image):
    """Create image and text response artifacts."""
    image_reference = ImageReference(
        name="original",
        location=str(tmp_path / "original.png"),
    )
    ImageContent(data=image).dematerialize(image_reference)

    response_reference = TextReference(
        name="response",
        location=str(tmp_path / "response.txt"),
    )
    TextContent(data=RESPONSE).dematerialize(response_reference)

    return image_reference, response_reference


@pytest.fixture
def output_reference(tmp_path) -> DetectionReference:
    """Provide the destination of the detections."""
    return DetectionReference(
        name="parsed_detections",
        location=str(tmp_path / "detections.json"),
    )


@pytest.fixture
def component(output_reference) -> TextDetectionParsingComponent:
    """Create a component that expects padded-square coordinates."""
    return TextDetectionParsingComponent(
        parser=TextDetectionParser("normalized_padded_square"),
        output_reference=output_reference,
    )


def test_prepare_loads_artifact_contents(component, artifacts, image):
    """Return the image and response contents instead of raw data."""
    image_content, response_content = component.prepare(list(artifacts))

    assert isinstance(image_content, ImageContent)
    assert isinstance(response_content, TextContent)
    np.testing.assert_array_equal(image_content.data, image)
    assert response_content.data == RESPONSE


def test_prepare_rejects_invalid_artifacts(tmp_path, component, artifacts):
    """Require exactly an ImageReference and a TextReference in order."""
    image_reference, response_reference = artifacts
    detection_reference = DetectionReference(
        name="other",
        location=str(tmp_path / "other.json"),
    )

    invalid_inputs = [
        [],
        [image_reference],
        [response_reference, image_reference],
        [image_reference, detection_reference],
        [image_reference, response_reference, response_reference],
    ]

    for input_artifacts in invalid_inputs:
        with pytest.raises(ValueError, match="ImageReference and a TextReference"):
            component.prepare(input_artifacts)


def test_execute_saves_converted_detections(component, artifacts, output_reference):
    """Convert boxes with the image size and save them in the existing format."""
    result = component.execute(component.prepare(list(artifacts)))

    assert result == [output_reference]
    assert output_reference.materialize().data == [
        Detection(cls="WBC", conf=None, box=[10, 10, 50, 40]),
    ]

    saved = json.loads(Path(output_reference.location).read_text(encoding="utf-8"))
    assert saved == [{"cls": "WBC", "conf": None, "box": [10.0, 10.0, 50.0, 40.0]}]


def test_execute_saves_empty_list(component, output_reference, image):
    """Save a valid empty artifact when the response reports no objects."""
    component.execute((ImageContent(data=image), TextContent(data="[]")))

    assert output_reference.materialize().data == []


@pytest.mark.parametrize(
    "response",
    [
        "No white blood cells.",
        '[{"cls": "WBC", "box": [0.1, 0.35, 0.5, 0.65]}, {"cls": "RBC"}]',
        (
            '[{"cls": "WBC", "box": [0.1, 0.35, 0.5, 0.65]}, '
            '{"cls": "RBC", "cls": "WBC", "box": [0.1, 0.35, 0.5, 0.65]}]'
        ),
        '[{"cls": "WBC ", "box": [0.1, 0.35, 0.5, 0.65]}]',
        '[{"cls": "WBC", "box": [0.1, true, 0.5, 0.65]}]',
    ],
)
def test_execute_writes_nothing_for_invalid_response(
    component, output_reference, image, response
):
    """Do not create a detection artifact, not even a partial one."""
    with pytest.raises(ValueError):
        component.execute((ImageContent(data=image), TextContent(data=response)))

    assert not Path(output_reference.location).exists()


def test_execute_rejects_invalid_prepared_data(component, output_reference, image):
    """Reject data that is not an ImageContent and a TextContent."""
    image_content = ImageContent(data=image)
    response_content = TextContent(data="[]")

    invalid_inputs = [
        None,
        (image_content,),
        (response_content, image_content),
        (image, response_content),
        (image_content, "[]"),
        (image_content, DetectionContent(data=[])),
    ]

    for prepared_data in invalid_inputs:
        with pytest.raises(TypeError):
            component.execute(prepared_data)

    assert not Path(output_reference.location).exists()
