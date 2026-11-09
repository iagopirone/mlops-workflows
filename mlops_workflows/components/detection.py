"""Define the result of object detection."""

from pydantic import BaseModel, Field


class Detection(BaseModel):
    """Represent one detected object and its bounding box."""

    cls: str
    conf: float = Field(ge=0.0, le=1.0)
    box: list[float] = Field(min_length=4, max_length=4)
