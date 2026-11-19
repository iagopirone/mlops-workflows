"""Define the interface for visual question answering models."""

from abc import ABC, abstractmethod

import numpy as np


class VisualQuestionAnswerer(ABC):
    """Define a common interface for answering questions about images."""

    @abstractmethod
    def answer(self, image: np.ndarray, question: str) -> str:
        """Answer a question about a BGR image with free text."""
        raise NotImplementedError
