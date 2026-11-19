"""Define the result of object detection."""

from typing import Annotated

from pydantic import BaseModel, Field


class Detection(BaseModel):
    """Represent one detected object and its bounding box.

    ``conf`` is required but may be ``None`` when the source provides no
    detection confidence (for example, boxes parsed from model text). It is
    never filled with an invented value.
    """

    cls: str
    conf: Annotated[float, Field(ge=0.0, le=1.0)] | None
    box: list[float] = Field(min_length=4, max_length=4)
