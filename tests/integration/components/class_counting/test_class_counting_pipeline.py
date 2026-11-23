"""Integration tests for counting detections saved by other components."""

import json

import numpy as np

from mlops_workflows.artifacts.class_count.class_count_reference import (
    ClassCountReference,
)
from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.artifacts.image.image_content import ImageContent
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.artifacts.text.text_content import TextContent
from mlops_workflows.artifacts.text.text_reference import TextReference
from mlops_workflows.components.class_counting.class_counting_component import (
    ClassCountingComponent,
)
from mlops_workflows.components.object_detection.object_detection_component import (
    ObjectDetectionComponent,
)
from mlops_workflows.components.object_detection.object_detector import ObjectDetector
from mlops_workflows.components.text_detection_parsing.text_detection_parser import (
    TextDetectionParser,
)
from mlops_workflows.components.text_detection_parsing.text_detection_parsing_component import (
    TextDetectionParsingComponent,
)


class FakeDetector(ObjectDetector):
    """Return predefined detections without running a model."""

    def detect(self, image: np.ndarray) -> list[Detection]:
        return [
            Detection(cls="RBC", conf=0.9, box=[1.0, 1.0, 10.0, 10.0]),
            Detection(cls="RBC", conf=0.4, box=[12.0, 12.0, 20.0, 20.0]),
            Detection(cls="WBC", conf=0.8, box=[30.0, 30.0, 50.0, 50.0]),
            Detection(cls="Bacteria", conf=0.7, box=[5.0, 40.0, 15.0, 55.0]),
        ]


def save_image(tmp_path) -> ImageReference:
    """Save a blank image and return its reference."""
    image_reference = ImageReference(
        name="image",
        location=str(tmp_path / "image.png"),
    )
    ImageContent(data=np.zeros((64, 64, 3), dtype=np.uint8)).dematerialize(
        image_reference
    )
    return image_reference


def test_object_detection_to_class_counting(tmp_path):
    """Count the detections saved by the object detection component."""
    image_reference = save_image(tmp_path)
    detection_reference = DetectionReference(
        name="detections",
        location=str(tmp_path / "detections.json"),
    )
    count_reference = ClassCountReference(
        name="counts",
        location=str(tmp_path / "counts.json"),
    )

    detection_component = ObjectDetectionComponent(FakeDetector(), detection_reference)
    detection_outputs = detection_component.execute(
        detection_component.prepare([image_reference])
    )
    saved_detections = (tmp_path / "detections.json").read_text("utf-8")

    counting_component = ClassCountingComponent(
        ["RBC", "WBC", "Platelets"], count_reference
    )
    count_outputs = counting_component.execute(
        counting_component.prepare(detection_outputs)
    )

    class_count = count_reference.materialize().data

    assert count_outputs == [count_reference]
    assert class_count.counts == {"RBC": 2, "WBC": 1, "Platelets": 0}
    assert class_count.total == 3
    assert class_count.excluded == {"Bacteria": 1}
    assert class_count.detection_count == 4
    assert (tmp_path / "detections.json").read_text("utf-8") == saved_detections


def test_text_detection_parsing_to_class_counting(tmp_path):
    """Count detections parsed from text, which have no confidence."""
    image_reference = save_image(tmp_path)
    response_reference = TextReference(
        name="response",
        location=str(tmp_path / "response.txt"),
    )
    TextContent(
        data=json.dumps(
            [
                {"cls": "white blood cell", "box": [10, 10, 30, 30]},
                {"cls": "red blood cell", "box": [40, 40, 60, 60]},
                {"cls": "white blood cell", "box": [5, 35, 25, 55]},
            ]
        )
    ).dematerialize(response_reference)
    detection_reference = DetectionReference(
        name="detections",
        location=str(tmp_path / "detections.json"),
    )
    count_reference = ClassCountReference(
        name="counts",
        location=str(tmp_path / "counts.json"),
    )

    parsing_component = TextDetectionParsingComponent(
        TextDetectionParser("pixel"),
        detection_reference,
    )
    detection_outputs = parsing_component.execute(
        parsing_component.prepare([image_reference, response_reference])
    )

    counting_component = ClassCountingComponent(None, count_reference)
    counting_component.execute(counting_component.prepare(detection_outputs))

    class_count = count_reference.materialize().data

    assert class_count.counts == {"white blood cell": 2, "red blood cell": 1}
    assert class_count.total == 3
