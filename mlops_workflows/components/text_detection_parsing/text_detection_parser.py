"""Convert model text responses into validated object detections."""

import json
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from mlops_workflows.artifacts.detection.detection import Detection

CoordinateFormat = Literal["pixel", "normalized_image", "normalized_padded_square"]
"""Coordinate convention of the boxes in the text response.

- ``pixel``: ``[x1, y1, x2, y2]`` in pixels of the original image.
- ``normalized_image``: values in ``[0, 1]`` relative to the original image.
- ``normalized_padded_square``: values in ``[0, 1]`` relative to a square of
  side ``max(width, height)`` with the image centered on it, as produced by
  LLaVA-style ``expand2square`` preprocessing.
"""

FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]


class TextDetection(BaseModel):
    """Validate one detection written by a model, without confidence."""

    model_config = ConfigDict(strict=True, extra="forbid")

    cls: str
    box: list[FiniteFloat] = Field(min_length=4, max_length=4)

    @field_validator("cls")
    @classmethod
    def validate_cls(cls, value: str) -> str:
        """Reject empty class names and surrounding whitespace."""
        if not value.strip():
            raise ValueError("The class name must not be blank.")

        if value != value.strip():
            raise ValueError("The class name must not start or end with whitespace.")

        return value


class TextDetectionParser:
    """Parse a JSON list of detections and convert boxes to image pixels.

    The expected text is exactly a JSON list such as
    ``[{"cls": "WBC", "box": [x1, y1, x2, y2]}]``, matching the format saved by
    ``DetectionContent`` without the ``conf`` field. An empty list means that
    no objects were reported. Duplicate keys in any JSON object make the
    response invalid. Any invalid item rejects the whole response.

    Parsing guarantees structural validity only; it cannot tell whether a box
    actually contains the named object.
    """

    def __init__(self, coordinate_format: CoordinateFormat):
        if coordinate_format not in get_args(CoordinateFormat):
            raise ValueError(f"Unsupported coordinate format: {coordinate_format!r}")

        self.coordinate_format = coordinate_format

    def parse(
        self,
        text: str,
        image_width: int,
        image_height: int,
    ) -> list[Detection]:
        """Return pixel-space detections with ``conf=None``."""
        if not isinstance(text, str):
            raise TypeError("The response must be a string.")

        # bool is a subclass of int, so it must be excluded explicitly.
        if (
            not isinstance(image_width, int)
            or not isinstance(image_height, int)
            or isinstance(image_width, bool)
            or isinstance(image_height, bool)
            or image_width <= 0
            or image_height <= 0
        ):
            raise ValueError("Image dimensions must be positive integers.")

        try:
            data = json.loads(
                text,
                parse_constant=_reject_constant,
                object_pairs_hook=_reject_duplicate_keys,
            )
        except ValueError as error:
            raise ValueError(f"The response is not valid JSON: {error}") from error

        # A wrong JSON shape is malformed model output, not a programming error,
        # so it raises ValueError like every other invalid response.
        if not isinstance(data, list):
            raise ValueError(  # noqa: TRY004
                "The response must be a JSON list of detections."
            )

        detections = []

        for index, item in enumerate(data):
            try:
                parsed = TextDetection.model_validate(item)
                box = self._to_pixels(parsed.box, image_width, image_height)
            except (ValidationError, ValueError) as error:
                raise ValueError(
                    f"Invalid detection at index {index}: {error}"
                ) from error

            detections.append(Detection(cls=parsed.cls, conf=None, box=box))

        return detections

    def _to_pixels(
        self,
        box: list[float],
        width: int,
        height: int,
    ) -> list[float]:
        """Validate a box in its declared space and convert it to pixels."""
        x1, y1, x2, y2 = box

        if x2 <= x1 or y2 <= y1:
            raise ValueError("Expected x1 < x2 and y1 < y2.")

        if self.coordinate_format == "pixel":
            if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
                raise ValueError("Pixel box is outside the image.")

            return [x1, y1, x2, y2]

        if min(box) < 0 or max(box) > 1:
            raise ValueError("Normalized coordinates must be within [0, 1].")

        if self.coordinate_format == "normalized_image":
            return [x1 * width, y1 * height, x2 * width, y2 * height]

        # normalized_padded_square: undo the centered square padding.
        side = max(width, height)
        offset_x = (side - width) // 2
        offset_y = (side - height) // 2

        x1 = min(max(x1 * side - offset_x, 0), width)
        y1 = min(max(y1 * side - offset_y, 0), height)
        x2 = min(max(x2 * side - offset_x, 0), width)
        y2 = min(max(y2 * side - offset_y, 0), height)

        if x2 <= x1 or y2 <= y1:
            raise ValueError("Box lies entirely in the padding area.")

        return [x1, y1, x2, y2]


def _reject_constant(name: str) -> float:
    """Reject NaN and Infinity, which Python's JSON parser accepts."""
    raise ValueError(f"Invalid JSON number: {name}")


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Build a JSON object, rejecting keys that appear more than once.

    Python's JSON parser silently keeps the last value of a duplicate key,
    which would hide ambiguous model output.
    """
    result = {}

    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key!r}")

        result[key] = value

    return result
