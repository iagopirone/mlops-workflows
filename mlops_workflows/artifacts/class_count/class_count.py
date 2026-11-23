"""Define the result of counting detections by class."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(ge=1)]


class ClassCount(BaseModel):
    """Hold per-class detection counts and the detections left out.

    ``classes`` is the configured domain: ``None`` counts every class found,
    a list counts only those classes (an empty list counts none). Class names
    are kept exactly as received; they are never stripped or case-folded.

    ``counts`` holds the counted classes, ``total`` their sum, ``excluded`` the
    detected classes outside the domain and ``detection_count`` the number of
    detections received, so ``total + sum(excluded) == detection_count``.
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    classes: list[str] | None
    counts: dict[str, NonNegativeInt]
    total: NonNegativeInt
    excluded: dict[str, PositiveInt]
    detection_count: NonNegativeInt

    @model_validator(mode="after")
    def check_consistency(self) -> "ClassCount":
        """Reject counts that do not add up or do not match the domain."""
        if self.total != sum(self.counts.values()):
            raise ValueError("The total must equal the sum of the counts.")

        if self.detection_count != self.total + sum(self.excluded.values()):
            raise ValueError(
                "The detection count must equal the total plus the excluded."
            )

        if self.classes is None:
            if self.excluded:
                raise ValueError("Generic counting cannot exclude classes.")
            if any(count == 0 for count in self.counts.values()):
                raise ValueError("Generic counting only lists detected classes.")
            return self

        if len(set(self.classes)) != len(self.classes):
            raise ValueError("The configured classes must be unique.")

        if list(self.counts) != self.classes:
            raise ValueError("The counts must list the configured classes in order.")

        if set(self.excluded) & set(self.classes):
            raise ValueError("Excluded classes must be outside the configured ones.")

        return self
