"""Test parsing model text responses into detections."""

import json

import pytest

from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.components.text_detection_parsing.text_detection_parser import (
    TextDetectionParser,
)


def _response(*items: dict) -> str:
    """Build a JSON response from detection items."""
    return json.dumps(list(items))


def test_parses_pixel_boxes_without_inventing_confidence():
    """Keep pixel coordinates and leave the confidence empty."""
    parser = TextDetectionParser("pixel")

    detections = parser.parse(
        _response(
            {"cls": "WBC", "box": [10, 20, 60, 80]},
            {"cls": "RBC", "box": [0.5, 1.5, 100, 50]},
        ),
        image_width=100,
        image_height=80,
    )

    assert detections == [
        Detection(cls="WBC", conf=None, box=[10, 20, 60, 80]),
        Detection(cls="RBC", conf=None, box=[0.5, 1.5, 100, 50]),
    ]
    assert all(detection.conf is None for detection in detections)


def test_accepts_surrounding_whitespace():
    """Accept a JSON document surrounded only by whitespace."""
    parser = TextDetectionParser("pixel")

    detections = parser.parse('\n  [{"cls": "cat", "box": [1, 2, 3, 4]}]  \n', 10, 10)

    assert detections[0].cls == "cat"


def test_empty_list_means_no_detections():
    """Treat an explicit empty list as a valid response without objects."""
    parser = TextDetectionParser("normalized_image")

    assert parser.parse("[]", 100, 100) == []


@pytest.mark.parametrize(
    ("width", "height", "box", "expected"),
    [
        (200, 100, [0.1, 0.2, 0.5, 0.6], [20, 20, 100, 60]),
        (200, 100, [0, 0, 1, 1], [0, 0, 200, 100]),
    ],
)
def test_converts_image_normalized_boxes(width, height, box, expected):
    """Scale normalized coordinates by the image size."""
    parser = TextDetectionParser("normalized_image")

    detections = parser.parse(_response({"cls": "a", "box": box}), width, height)

    assert detections[0].box == pytest.approx(expected)


@pytest.mark.parametrize(
    ("width", "height", "box", "expected"),
    [
        # Landscape: side 100, vertical offset 25.
        (100, 50, [0.1, 0.35, 0.5, 0.65], [10, 10, 50, 40]),
        # Portrait: side 100, horizontal offset 25.
        (50, 100, [0.35, 0.1, 0.65, 0.5], [10, 10, 40, 50]),
        # Square: no padding.
        (80, 80, [0.25, 0.25, 0.5, 0.5], [20, 20, 40, 40]),
        # Odd padding: side 100, vertical offset (100 - 51) // 2 = 24.
        (100, 51, [0.0, 0.5, 1.0, 0.7], [0, 26, 100, 46]),
        # Partly in the padding: clipped to the image.
        (100, 50, [0.1, 0.1, 0.5, 0.4], [10, 0, 50, 15]),
    ],
)
def test_converts_padded_square_boxes(width, height, box, expected):
    """Undo centered square padding and clip to the image."""
    parser = TextDetectionParser("normalized_padded_square")

    detections = parser.parse(_response({"cls": "a", "box": box}), width, height)

    assert detections[0].box == pytest.approx(expected)


def test_rejects_box_entirely_in_padding():
    """Reject a box that does not cover any image pixel."""
    parser = TextDetectionParser("normalized_padded_square")

    with pytest.raises(ValueError, match="padding"):
        parser.parse(_response({"cls": "a", "box": [0.1, 0.0, 0.5, 0.2]}), 100, 50)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "There are two cells in the image.",
        '[{"cls": "a", "box": [1, 2, 3, 4]}',
        '```json\n[{"cls": "a", "box": [1, 2, 3, 4]}]\n```',
        'Answer: [{"cls": "a", "box": [1, 2, 3, 4]}]',
    ],
)
def test_rejects_malformed_or_embedded_json(text):
    """Accept only a JSON document, not free text or Markdown."""
    parser = TextDetectionParser("pixel")

    with pytest.raises(ValueError, match="not valid JSON"):
        parser.parse(text, 10, 10)


@pytest.mark.parametrize(
    "text",
    ['{"cls": "a", "box": [1, 2, 3, 4]}', '{"detections": []}', "null", "3"],
)
def test_rejects_json_that_is_not_a_list(text):
    """Require a top-level JSON list."""
    parser = TextDetectionParser("pixel")

    with pytest.raises(ValueError, match="JSON list"):
        parser.parse(text, 10, 10)


@pytest.mark.parametrize(
    "item",
    [
        {"box": [1, 2, 3, 4]},
        {"cls": "a"},
        {"cls": "", "box": [1, 2, 3, 4]},
        {"cls": "   ", "box": [1, 2, 3, 4]},
        {"cls": 7, "box": [1, 2, 3, 4]},
        {"cls": "a", "box": [1, 2, 3]},
        {"cls": "a", "box": [1, 2, 3, 4, 5]},
        {"cls": "a", "box": "1, 2, 3, 4"},
        {"cls": "a", "box": ["1", 2, 3, 4]},
        {"cls": "a", "box": [True, 2, 3, 4]},
        {"cls": "a", "box": [None, 2, 3, 4]},
        {"cls": "a", "box": [1, 2, 3, 4], "conf": 0.9},
        {"cls": "a", "box": [1, 2, 3, 4], "confidence": 0.9},
        "not an object",
    ],
)
def test_rejects_incomplete_or_invalid_items(item):
    """Reject missing fields, wrong types and model-written confidence."""
    parser = TextDetectionParser("pixel")

    with pytest.raises(ValueError, match="index 0"):
        parser.parse(_response(item), 10, 10)


@pytest.mark.parametrize(
    "number",
    ["NaN", "Infinity", "-Infinity", "1e400"],
)
def test_rejects_non_finite_coordinates(number):
    """Reject NaN and infinite values, including overflowing literals."""
    parser = TextDetectionParser("pixel")
    text = f'[{{"cls": "a", "box": [{number}, 2, 3, 4]}}]'

    with pytest.raises(ValueError):
        parser.parse(text, 10, 10)


@pytest.mark.parametrize(
    ("coordinate_format", "box"),
    [
        ("pixel", [5, 2, 5, 4]),
        ("pixel", [6, 2, 5, 4]),
        ("pixel", [1, 4, 3, 2]),
        ("pixel", [-1, 2, 3, 4]),
        ("pixel", [1, 2, 11, 4]),
        ("pixel", [1, 2, 3, 11]),
        ("normalized_image", [0.1, 0.1, 1.2, 0.5]),
        ("normalized_image", [-0.1, 0.1, 0.5, 0.5]),
        ("normalized_image", [0.5, 0.1, 0.2, 0.5]),
        ("normalized_padded_square", [0.1, 0.1, 1.5, 0.5]),
    ],
)
def test_rejects_unordered_or_out_of_range_boxes(coordinate_format, box):
    """Reject boxes that are unordered or outside their declared space."""
    parser = TextDetectionParser(coordinate_format)

    with pytest.raises(ValueError, match="index 0"):
        parser.parse(_response({"cls": "a", "box": box}), 10, 10)


def test_one_invalid_item_rejects_the_whole_response():
    """Do not return a partial list when any item is invalid."""
    parser = TextDetectionParser("pixel")

    with pytest.raises(ValueError, match="index 1"):
        parser.parse(
            _response(
                {"cls": "a", "box": [1, 2, 3, 4]},
                {"cls": "b", "box": [1, 2]},
                {"cls": "c", "box": [1, 2, 3, 4]},
            ),
            10,
            10,
        )


def test_rejects_unknown_coordinate_format():
    """Require one of the documented coordinate conventions."""
    with pytest.raises(ValueError, match="Unsupported coordinate format"):
        TextDetectionParser("normalized")


@pytest.mark.parametrize(
    ("width", "height"),
    [(0, 10), (10, 0), (-1, 10), (10.0, 10)],
)
def test_rejects_invalid_image_dimensions(width, height):
    """Require positive integer image dimensions."""
    parser = TextDetectionParser("pixel")

    with pytest.raises(ValueError, match="positive integers"):
        parser.parse("[]", width, height)


def test_rejects_non_string_response():
    """Require the response to be text."""
    parser = TextDetectionParser("pixel")

    with pytest.raises(TypeError):
        parser.parse(b"[]", 10, 10)


# Regression tests for the review findings of 2026-11-17 (P1-P3).


@pytest.mark.parametrize(
    "text",
    [
        '[{"cls": "a", "cls": "b", "box": [1, 2, 3, 4]}]',
        '[{"cls": "a", "box": [1, 2, 3, 4], "box": [5, 6, 7, 8]}]',
        '[{"cls": "a", "box": [1, 2, 3, 4], "extra": {"x": 1, "x": 2}}]',
        '[{"cls": "a", "box": [1, 2, 3, 4]}, {"cls": "b", "cls": "b", "box": [1, 2, 3, 4]}]',
    ],
)
def test_rejects_duplicate_json_keys(text):
    """P1: reject duplicate keys in any object instead of keeping the last one."""
    parser = TextDetectionParser("pixel")

    with pytest.raises(ValueError, match="Duplicate JSON key"):
        parser.parse(text, 10, 10)


def test_same_keys_in_different_objects_are_allowed():
    """P1: keys may repeat across objects, only not within one object."""
    parser = TextDetectionParser("pixel")

    detections = parser.parse(
        '[{"cls": "a", "box": [1, 2, 3, 4]}, {"cls": "b", "box": [5, 6, 7, 8]}]',
        10,
        10,
    )

    assert [detection.cls for detection in detections] == ["a", "b"]


@pytest.mark.parametrize(
    "cls",
    [" WBC", "WBC ", " WBC ", "\tWBC", "WBC\n", " WBC", "", " ", "\n\t"],
)
def test_rejects_empty_or_padded_class_names(cls):
    """P2: reject empty class names and leading or trailing whitespace."""
    parser = TextDetectionParser("pixel")

    with pytest.raises(ValueError, match="index 0"):
        parser.parse(_response({"cls": cls, "box": [1, 2, 3, 4]}), 10, 10)


def test_accepts_inner_spaces_in_class_names():
    """P2: keep multi-word class names unchanged."""
    parser = TextDetectionParser("pixel")

    detections = parser.parse(
        _response({"cls": "white blood cell", "box": [1, 2, 3, 4]}), 10, 10
    )

    assert detections[0].cls == "white blood cell"


@pytest.mark.parametrize("position", [0, 1, 2, 3])
@pytest.mark.parametrize("value", [True, False])
@pytest.mark.parametrize(
    "coordinate_format",
    ["pixel", "normalized_image", "normalized_padded_square"],
)
def test_rejects_boolean_coordinates(coordinate_format, value, position):
    """P3: reject JSON booleans in any box position for every format."""
    parser = TextDetectionParser(coordinate_format)
    box = [0.1, 0.2, 0.6, 0.8]
    box[position] = value

    with pytest.raises(ValueError, match="index 0"):
        parser.parse(_response({"cls": "a", "box": box}), 10, 10)


@pytest.mark.parametrize(
    ("width", "height"),
    [(True, 10), (10, True), (True, True), (False, 10)],
)
def test_rejects_boolean_image_dimensions(width, height):
    """P3: reject booleans as image dimensions even though bool is an int."""
    parser = TextDetectionParser("pixel")

    with pytest.raises(ValueError, match="positive integers"):
        parser.parse("[]", width, height)


def test_duplicate_key_in_one_item_rejects_whole_response():
    """Keep strict validation: valid items are not returned partially."""
    parser = TextDetectionParser("pixel")
    text = (
        '[{"cls": "a", "box": [1, 2, 3, 4]},'
        ' {"cls": "b", "box": [1, 2, 3, 4], "box": [1, 2, 3, 5]}]'
    )

    with pytest.raises(ValueError, match="Duplicate JSON key"):
        parser.parse(text, 10, 10)
