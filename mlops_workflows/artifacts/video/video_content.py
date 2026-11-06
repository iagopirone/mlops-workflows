"""Store and save video frames without audio."""

from pathlib import Path

import cv2
import numpy as np
from pydantic import ConfigDict, Field

from mlops_workflows.artifacts.content import ArtifactContent
from mlops_workflows.artifacts.interface import ArtifactReference


class VideoContent(ArtifactContent):
    """Store video frames and their playback rate."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: list[np.ndarray] = Field(min_length=1)
    fps: float = Field(gt=0, allow_inf_nan=False)

    def validate_frames(self) -> None:
        """Check that all frames are valid BGR images of equal size."""
        if not self.data:
            raise ValueError("The video must contain at least one frame.")

        expected_shape = None

        for frame in self.data:
            if not isinstance(frame, np.ndarray):
                raise TypeError("Each frame must be a NumPy array.")

            if (
                frame.dtype != np.uint8
                or frame.ndim != 3
                or frame.shape[2] != 3
                or frame.size == 0
            ):
                raise ValueError("Each frame must be a nonempty uint8 BGR image.")

            if expected_shape is None:
                expected_shape = frame.shape
            elif frame.shape != expected_shape:
                raise ValueError("All frames must have the same size.")

    def dematerialize(self, reference: ArtifactReference) -> str:
        """Save the frames and return the destination location."""
        self.validate_frames()

        path = Path(reference.location)
        codecs = {".avi": "MJPG", ".mp4": "mp4v"}
        codec = codecs.get(path.suffix.lower())

        if codec is None:
            raise ValueError("The destination must use .avi or .mp4.")

        height, width = self.data[0].shape[:2]
        path.parent.mkdir(parents=True, exist_ok=True)

        writer = cv2.VideoWriter(
            str(path),
            cv2.VideoWriter_fourcc(*codec),
            self.fps,
            (width, height),
        )

        try:
            if not writer.isOpened():
                raise OSError(f"Could not create the video: {path}")

            for frame in self.data:
                writer.write(frame)
        finally:
            writer.release()

        return reference.location
