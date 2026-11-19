"""Convert Florence-2 structured outputs into project detections (experimental).

Florence-2's processor already returns ``{task: {"bboxes": [[x1, y1, x2, y2],
...], "labels": [...]}}`` in pixels of the original image (bins dequantized at
bin centres). This adapter only validates that structure and copies it into
``Detection`` objects; it never changes coordinates, never maps labels to
project classes and always sets ``conf=None`` because Florence-2 gives no
confidence. ``TextDetectionParser`` (MIRAGE JSON) is not involved.
"""

import math

from mlops_workflows.artifacts.detection.detection import Detection

DETECTION_TASKS = ("<OD>", "<CAPTION_TO_PHRASE_GROUNDING>")


class FlorenceOutputError(ValueError):
    """The structured output is not a valid list of boxes for this image."""


def class_source(task: str) -> str:
    """``model`` when Florence-2 names the objects, ``prompt`` when it grounds a phrase."""
    return "model" if task == "<OD>" else "prompt"


def florence_to_detections(
    parsed: object, task: str, width: int, height: int, phrase: str | None = None
) -> list[Detection]:
    """Validate one parsed Florence-2 answer and return pixel detections.

    The whole answer is rejected if any box or label is invalid. For phrase
    grounding an empty label is replaced by the prompt phrase (the class then
    comes from the prompt, see ``class_source``).
    """
    if task not in DETECTION_TASKS:
        raise ValueError(f"Unsupported task: {task!r}")
    if not isinstance(parsed, dict) or set(parsed) != {task}:
        raise FlorenceOutputError(f"Expected exactly the key {task!r}.")
    result = parsed[task]
    if not isinstance(result, dict) or not {"bboxes", "labels"} <= set(result):
        raise FlorenceOutputError("Expected 'bboxes' and 'labels'.")
    boxes, labels = result["bboxes"], result["labels"]
    if not isinstance(boxes, list) or not isinstance(labels, list):
        raise FlorenceOutputError("'bboxes' and 'labels' must be lists.")
    if len(boxes) != len(labels):
        raise FlorenceOutputError(
            f"{len(boxes)} boxes but {len(labels)} labels; cannot pair them."
        )

    detections = []
    for index, (box, label) in enumerate(zip(boxes, labels, strict=True)):
        if (
            not isinstance(box, list)
            or len(box) != 4
            or not all(
                isinstance(v, int | float) and not isinstance(v, bool) for v in box
            )
            or not all(math.isfinite(v) for v in box)
        ):
            raise FlorenceOutputError(f"Box {index} is not four finite numbers.")
        x1, y1, x2, y2 = (float(v) for v in box)
        if x2 <= x1 or y2 <= y1:
            raise FlorenceOutputError(f"Box {index} needs x1 < x2 and y1 < y2.")
        if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
            raise FlorenceOutputError(
                f"Box {index} is outside the {width}x{height} image."
            )
        if not isinstance(label, str):
            raise FlorenceOutputError(f"Label {index} is not text.")
        name = label.strip()
        if not name and task == "<CAPTION_TO_PHRASE_GROUNDING>" and phrase:
            name = phrase
        if not name:
            raise FlorenceOutputError(f"Label {index} is empty.")
        detections.append(Detection(cls=name, conf=None, box=[x1, y1, x2, y2]))
    return detections


def area_fraction(box: list[float], width: int, height: int) -> float:
    """Fraction of the image covered by a box (diagnostic for whole-image boxes)."""
    x1, y1, x2, y2 = box
    return (x2 - x1) * (y2 - y1) / (width * height)
