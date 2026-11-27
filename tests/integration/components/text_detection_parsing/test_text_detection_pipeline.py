"""Integration test: image + prompt -> text answer -> detections -> annotated image."""

import numpy as np
import pytest

from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.artifacts.image.image_content import ImageContent
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.artifacts.text.text_content import TextContent
from mlops_workflows.artifacts.text.text_reference import TextReference
from mlops_workflows.components.detection_visualization.detection_visualization_component import (
    DetectionVisualizationComponent,
)
from mlops_workflows.components.text_detection_parsing.text_detection_parser import (
    TextDetectionParser,
)
from mlops_workflows.components.text_detection_parsing.text_detection_parsing_component import (
    TextDetectionParsingComponent,
)
from mlops_workflows.components.visual_question_answering.visual_question_answerer import (
    VisualQuestionAnswerer,
)
from mlops_workflows.components.visual_question_answering.visual_question_answering_component import (
    VisualQuestionAnsweringComponent,
)


class FakeAnswerer(VisualQuestionAnswerer):
    """Return a fixed text response instead of running a multimodal model."""

    def __init__(self, response: str):
        self.response = response

    def answer(self, image: np.ndarray, question: str) -> str:
        """Return the predefined response."""
        return self.response


def _run_pipeline(tmp_path, response: str):
    """Run VQA, parsing and visualization with artifacts on disk."""
    image_reference = ImageReference(
        name="original",
        location=str(tmp_path / "original.png"),
    )
    prompt_reference = TextReference(
        name="prompt",
        location=str(tmp_path / "prompt.txt"),
    )
    answer_reference = TextReference(
        name="answer",
        location=str(tmp_path / "answer.txt"),
    )
    detection_reference = DetectionReference(
        name="detections",
        location=str(tmp_path / "detections.json"),
    )
    annotated_reference = ImageReference(
        name="annotated",
        location=str(tmp_path / "annotated.png"),
    )

    image = np.zeros((50, 100, 3), dtype=np.uint8)
    ImageContent(data=image).dematerialize(image_reference)
    TextContent(data="Locate the white blood cell.").dematerialize(prompt_reference)

    vqa = VisualQuestionAnsweringComponent(FakeAnswerer(response), answer_reference)
    answer_outputs = vqa.execute(vqa.prepare([image_reference, prompt_reference]))

    parsing = TextDetectionParsingComponent(
        parser=TextDetectionParser("normalized_padded_square"),
        output_reference=detection_reference,
    )
    detection_outputs = parsing.execute(
        parsing.prepare([image_reference, answer_outputs[0]])
    )

    visualization = DetectionVisualizationComponent(annotated_reference)
    visualization.execute(
        visualization.prepare([image_reference, detection_outputs[0]])
    )

    return image, image_reference, detection_reference, annotated_reference


def test_text_answer_to_annotated_image(tmp_path):
    """Draw boxes parsed from a simulated multimodal answer."""
    image, image_reference, detection_reference, annotated_reference = _run_pipeline(
        tmp_path,
        '[{"cls": "WBC", "box": [0.1, 0.35, 0.5, 0.65]}]',
    )

    detections = detection_reference.materialize().data
    annotated = annotated_reference.materialize().data

    assert len(detections) == 1
    assert detections[0].cls == "WBC"
    assert detections[0].conf is None
    assert detections[0].box == pytest.approx([10, 10, 50, 40])
    assert annotated[10, 10].tolist() == [0, 255, 0]
    np.testing.assert_array_equal(image_reference.materialize().data, image)


def test_invalid_answer_stops_before_detections(tmp_path):
    """Create no detection or annotated image when the answer is not JSON."""
    with pytest.raises(ValueError, match="not valid JSON"):
        _run_pipeline(tmp_path, "I can see one white blood cell.")

    assert (tmp_path / "answer.txt").is_file()
    assert not (tmp_path / "detections.json").exists()
    assert not (tmp_path / "annotated.png").exists()
