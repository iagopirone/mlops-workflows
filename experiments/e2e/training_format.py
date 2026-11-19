"""Experimental adapter for MIRAGE answers in its training localization format.

In MIRAGE's training data (LLaVA-1.5/RefCOCO style), the prompt "Please provide
the bounding box coordinate of the region this sentence describes: <text>" is
answered with ONE box as bracketed text, e.g. ``[0.07, 0.13, 0.7, 0.86]``. This
module accepts exactly that format and nothing else, and rewrites it as the JSON
the unchanged ``TextDetectionParser`` reads. Coordinates are validated and
converted to pixels by that parser (``normalized_padded_square``).

The class is NOT identified by the model: it comes from the prompt, so results
of this experiment are class-conditioned localization, not detection plus
classification, and must be reported separately from the JSON-prompt experiment.
"""

import json
import re

from experiments.e2e.bccd_annotations import CLASSES

TRAINING_PROMPT_PREFIX = (
    "Please provide the bounding box coordinate of the region this sentence describes: "
)
PROMPT_TEXT = {"WBC": "a white blood cell.", "RBC": "a red blood cell.", "Platelets": "a platelet."}  # fmt: skip
_NUMBER = r"(\d+(?:\.\d+)?)"
TRAINING_ANSWER = re.compile(
    r"^\s*\[\s*" + r"\s*,\s*".join([_NUMBER] * 4) + r"\s*\]\s*$"
)


class TrainingFormatError(ValueError):
    """The answer is not exactly one bracketed box of four numbers."""


def training_prompt(prompt_class: str) -> str:
    """Return the training-style grounding prompt for one class."""
    if prompt_class not in CLASSES:
        raise ValueError(f"Unknown class {prompt_class!r}; expected {CLASSES}.")
    return TRAINING_PROMPT_PREFIX + PROMPT_TEXT[prompt_class]


def training_answer_to_json(answer: str, prompt_class: str) -> str:
    """Rewrite one training-format box as ``[{"cls": prompt_class, "box": [...]}]``.

    Only ``[x1, y1, x2, y2]`` with plain non-negative decimals (surrounding
    whitespace allowed) is accepted. Range and order are checked later by the
    parser, which also converts to pixels.
    """
    if prompt_class not in CLASSES:
        raise ValueError(f"Unknown class {prompt_class!r}; expected {CLASSES}.")
    match = TRAINING_ANSWER.match(answer)
    if match is None:
        raise TrainingFormatError(
            "format_mismatch: expected exactly one box '[x1, y1, x2, y2]' "
            "with decimal numbers."
        )
    box = [float(value) for value in match.groups()]
    return json.dumps([{"cls": prompt_class, "box": box}])
