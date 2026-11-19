"""Test the experimental training-format adapter (no model involved)."""

import json
from pathlib import Path

import pytest

from experiments.e2e.training_format import (
    TrainingFormatError,
    training_answer_to_json,
    training_prompt,
)
from mlops_workflows.components.text_detection_parsing.text_detection_parser import (
    TextDetectionParser,
)

PROMPTS = Path(__file__).resolve().parents[2] / "mirage" / "prompts"


@pytest.mark.parametrize(
    "answer",
    ["[0.07, 0.13, 0.7, 0.86]", "  [0.07,0.13,0.7,0.86]\n", "[0, 0, 1, 1]"],
)
def test_accepts_exactly_one_bracketed_box(answer):
    converted = json.loads(training_answer_to_json(answer, "WBC"))

    assert len(converted) == 1
    assert converted[0]["cls"] == "WBC"
    assert len(converted[0]["box"]) == 4


def test_class_comes_from_the_prompt():
    converted = json.loads(training_answer_to_json("[0.1, 0.2, 0.3, 0.4]", "Platelets"))

    assert converted == [{"cls": "Platelets", "box": [0.1, 0.2, 0.3, 0.4]}]


@pytest.mark.parametrize(
    "answer",
    [
        "The cell is at [0.1, 0.2, 0.3, 0.4].",
        "[0.1, 0.2, 0.3]",
        "[0.1, 0.2, 0.3, 0.4, 0.5]",
        "[0.1, 0.2, 0.3, 0.4] [0.5, 0.5, 0.6, 0.6]",
        '[{"cls": "WBC", "box": [0.1, 0.2, 0.3, 0.4]}]',
        "[-0.1, 0.2, 0.3, 0.4]",
        "[1e-1, 0.2, 0.3, 0.4]",
        "[.1, 0.2, 0.3, 0.4]",
        "(0.1, 0.2, 0.3, 0.4)",
        "",
    ],
)
def test_rejects_anything_else(answer):
    with pytest.raises(TrainingFormatError, match="format_mismatch"):
        training_answer_to_json(answer, "WBC")


def test_unknown_prompt_class_is_rejected():
    with pytest.raises(ValueError, match="Unknown class"):
        training_answer_to_json("[0.1, 0.2, 0.3, 0.4]", "Neutrophil")


def test_parser_validates_range_and_converts_to_pixels():
    parser = TextDetectionParser("normalized_padded_square")
    # 80x60 image: square side 80, vertical padding 10.
    converted = training_answer_to_json("[0.125, 0.25, 0.5, 0.75]", "WBC")

    detections = parser.parse(converted, 80, 60)

    assert detections[0].box == [10.0, 10.0, 40.0, 50.0]
    assert detections[0].conf is None


def test_out_of_range_box_is_rejected_by_the_parser():
    converted = training_answer_to_json("[0.1, 0.2, 1.3, 0.4]", "WBC")

    with pytest.raises(ValueError, match="within"):
        TextDetectionParser("normalized_padded_square").parse(converted, 80, 60)


@pytest.mark.parametrize(
    ("cls", "file"),
    [("WBC", "grounding_wbc.txt"), ("RBC", "grounding_rbc.txt"),
     ("Platelets", "grounding_platelets.txt")],
)  # fmt: skip
def test_prompt_files_match_the_training_phrase(cls, file):
    assert (PROMPTS / file).read_text(encoding="utf-8").strip() == training_prompt(cls)
