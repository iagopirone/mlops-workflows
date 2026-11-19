"""Evaluate YOLO detections with the offline MIRAGE evaluator, unchanged.

The evaluator (``experiments.mirage.evaluate_detections.evaluate``) takes text
responses and a ``TextDetectionParser``. YOLO detections are written as the
pixel JSON that ``TextDetectionParser("pixel")`` accepts, so both models go
through the same validation, matching and metrics. ``conf`` is left out because
the parser rejects it in text and the matching never uses it; the YOLO
confidence threshold must therefore be reported next to the metrics.
"""

import json

from experiments.mirage.evaluate_detections import evaluate
from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.components.text_detection_parsing.text_detection_parser import (
    TextDetectionParser,
)


def detections_to_response(
    detections: list[Detection], label_mapping: dict[str, str] | None = None
) -> str:
    """Return detections as pixel-space JSON text without confidence.

    ``label_mapping`` renames labels by exact string match only (an explicit,
    recorded vocabulary mapping); any other label is kept unchanged.
    """
    mapping = label_mapping or {}
    return json.dumps(
        [{"cls": mapping.get(d.cls, d.cls), "box": d.box} for d in detections]
    )


def evaluate_detection_references(
    ground_truth: dict[str, dict[str, object]],
    references: dict[str, DetectionReference],
    iou_threshold: float,
    class_aware: bool = True,
    label_mapping: dict[str, str] | None = None,
) -> dict[str, object]:
    """Evaluate saved detections, keyed by image ID, against the annotations."""
    responses = {
        image_id: detections_to_response(reference.materialize().data, label_mapping)
        for image_id, reference in references.items()
    }
    return evaluate(
        ground_truth,
        responses,
        TextDetectionParser("pixel"),
        iou_threshold,
        class_aware=class_aware,
    )
