"""Identify and load local videos without audio."""

from pathlib import Path

import cv2

from mlops_workflows.artifacts.interface import ArtifactReference
from mlops_workflows.artifacts.video.video_content import VideoContent


class VideoReference(ArtifactReference):
    """Identify a video by its name and location."""

    def materialize(self) -> VideoContent:
        """Load the video frames in BGR format and their playback rate."""
        path = Path(self.location)

        if not path.is_file():
            raise FileNotFoundError(f"Video file not found: {path}")

        capture = cv2.VideoCapture(str(path))

        try:
            if not capture.isOpened():
                raise ValueError(f"Could not open the video: {path}")

            fps = capture.get(cv2.CAP_PROP_FPS)
            frames = []

            while True:
                success, frame = capture.read()

                if not success:
                    break

                frames.append(frame)

            if not frames:
                raise ValueError("The video has no readable frames.")

            return VideoContent(data=frames, fps=fps)
        finally:
            capture.release()
