"""Convert Qwen3-VL grounding answers into project detections (experimental).

The official Qwen3-VL 2D grounding cookbook asks for "bbox coordinates in JSON
format" and documents relative coordinates from 0 to 1000 on each axis
(``x / 1000 * width``, ``y / 1000 * height``). This adapter accepts exactly one
JSON array of ``{"bbox_2d": [x1, y1, x2, y2], "label": str}`` objects, either
as the whole answer or inside a single ```` ```json ```` fence, and converts it
with an explicitly chosen convention. It never swaps, clips or invents
coordinates, never maps labels to project classes and always sets
``conf=None``. ``TextDetectionParser`` (MIRAGE) is not involved.
"""

import json
import math
import re

from mlops_workflows.artifacts.detection.detection import Detection

CONVENTIONS = ("relative_1000", "pixel")
_NUM = r"\s*(-?\d+(?:\.\d+)?)\s*"
BOX_IN_TEXT = re.compile(r'"bbox_2d"\s*:\s*\[' + ",".join([_NUM] * 4) + r"\]")
FENCE = re.compile(r"^\s*```(?:json)?\s*\n(.*?)\n?\s*```\s*$", re.DOTALL)


class QwenOutputError(ValueError):
    """The answer is not a valid list of boxes for this image."""


def extract_json(answer: str) -> object:
    """Return the JSON value of the answer (whole text or one ```json fence)."""
    match = FENCE.match(answer)
    text = match.group(1) if match else answer
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise QwenOutputError(f"not JSON: {exc}") from exc


def qwen_to_detections(
    answer: str, convention: str, width: int, height: int
) -> list[Detection]:
    """Validate one answer and return pixel detections; reject it whole if invalid."""
    if convention not in CONVENTIONS:
        raise ValueError(f"Unsupported convention: {convention!r}")
    items = extract_json(answer)
    if not isinstance(items, list):
        raise QwenOutputError("Expected a JSON array of objects.")
    limit_x, limit_y = (
        (1000, 1000) if convention == "relative_1000" else (width, height)
    )
    detections = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or set(item) != {"bbox_2d", "label"}:
            raise QwenOutputError(
                f"Item {index} must have exactly 'bbox_2d' and 'label'."
            )
        box, label = item["bbox_2d"], item["label"]
        if (
            not isinstance(box, list)
            or len(box) != 4
            or not all(
                isinstance(v, int | float) and not isinstance(v, bool) for v in box
            )
            or not all(math.isfinite(v) for v in box)
        ):
            raise QwenOutputError(f"Item {index}: bbox_2d is not four finite numbers.")
        x1, y1, x2, y2 = (float(v) for v in box)
        if x2 <= x1 or y2 <= y1:
            raise QwenOutputError(f"Item {index}: needs x1 < x2 and y1 < y2.")
        if x1 < 0 or y1 < 0 or x2 > limit_x or y2 > limit_y:
            raise QwenOutputError(
                f"Item {index}: outside the {convention} range {limit_x}x{limit_y}."
            )
        if not isinstance(label, str) or not label.strip():
            raise QwenOutputError(f"Item {index}: label must be non-empty text.")
        if convention == "relative_1000":
            x1, x2 = x1 * width / 1000, x2 * width / 1000
            y1, y2 = y1 * height / 1000, y2 * height / 1000
        detections.append(Detection(cls=label.strip(), conf=None, box=[x1, y1, x2, y2]))
    return detections


def coordinate_evidence(answer: str, width: int, height: int) -> dict[str, object]:
    """Describe raw ``bbox_2d`` ranges to test the coordinate convention.

    Any x above ``width`` or y above ``height`` rules out pixel coordinates; any
    value above 1000 rules out the documented 0-1000 relative convention.
    """
    try:
        items = extract_json(answer)
    except QwenOutputError:
        parsed = False
        # Evidence only: well-formed "bbox_2d": [a, b, c, d] inside broken text.
        boxes = [
            [float(v) for v in match.groups()] for match in BOX_IN_TEXT.finditer(answer)
        ]
    else:
        parsed = True
        boxes = [
            item["bbox_2d"]
            for item in (items if isinstance(items, list) else [])
            if isinstance(item, dict)
            and isinstance(item.get("bbox_2d"), list)
            and len(item["bbox_2d"]) == 4
            and all(isinstance(v, int | float) for v in item["bbox_2d"])
        ]
    if not boxes:
        return {"parsed": parsed, "boxes": 0}
    max_x = max(max(b[0], b[2]) for b in boxes)
    max_y = max(max(b[1], b[3]) for b in boxes)
    return {
        "parsed": parsed,
        "boxes": len(boxes),
        "max_x": max_x,
        "max_y": max_y,
        "rules_out_pixel": max_x > width or max_y > height,
        "rules_out_relative_1000": max_x > 1000 or max_y > 1000,
    }
