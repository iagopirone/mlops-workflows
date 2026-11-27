"""Check that the offline evaluator can be reused for YOLO without changes."""

import json

from experiments.e2e.yolo_evaluation import (
    detections_to_response,
    evaluate_detection_references,
)
from experiments.mirage.evaluate_detections import match_detections
from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.artifacts.detection.detection_content import DetectionContent
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference


def save(tmp_path, name, detections):
    reference = DetectionReference(name=name, location=str(tmp_path / f"{name}.json"))
    DetectionContent(data=detections).dematerialize(reference)
    return reference


def gt(width, height, *objects):
    return {
        "width": width,
        "height": height,
        "objects": [{"cls": c, "box": b} for c, b in objects],
    }


def test_response_drops_confidence_and_keeps_boxes_exactly():
    detections = [Detection(cls="WBC", conf=0.87, box=[0.1, 2.25, 30.123456789, 40.0])]

    response = json.loads(detections_to_response(detections))

    assert response == [{"cls": "WBC", "box": [0.1, 2.25, 30.123456789, 40.0]}]


def test_metrics_match_direct_matching(tmp_path):
    annotations = [("WBC", [10, 10, 50, 50]), ("RBC", [60, 60, 90, 90])]
    detections = [
        Detection(cls="WBC", conf=0.9, box=[12.0, 11.0, 50.0, 49.0]),
        Detection(cls="RBC", conf=0.4, box=[0.0, 0.0, 5.0, 5.0]),
    ]
    ground_truth = {"a": gt(100, 100, *annotations)}

    report = evaluate_detection_references(
        ground_truth, {"a": save(tmp_path, "a", detections)}, 0.5
    )
    direct = match_detections(
        [{"cls": d.cls, "box": d.box} for d in detections],
        [{"cls": c, "box": b} for c, b in annotations],
        0.5,
    )

    image = report["images"][0]
    assert image["status"] == "valid"
    assert [
        (m["prediction_index"], m["annotation_index"]) for m in image["matches"]
    ] == [(p, a) for p, a, _ in direct]
    assert report["summary"]["true_positives"] == 1
    assert report["summary"]["false_positives"] == 1
    assert report["summary"]["false_negatives"] == 1


def test_confidence_does_not_change_metrics(tmp_path):
    ground_truth = {"a": gt(100, 100, ("WBC", [10, 10, 50, 50]))}
    low = [Detection(cls="WBC", conf=0.01, box=[10.0, 10.0, 50.0, 50.0])]
    high = [Detection(cls="WBC", conf=0.99, box=[10.0, 10.0, 50.0, 50.0])]

    first = evaluate_detection_references(
        ground_truth, {"a": save(tmp_path, "low", low)}, 0.5
    )
    second = evaluate_detection_references(
        ground_truth, {"a": save(tmp_path, "high", high)}, 0.5
    )

    assert first["summary"] == second["summary"]


def test_boxes_touching_image_border_are_accepted(tmp_path):
    # YoloDetector clips boxes to [0, width] x [0, height].
    ground_truth = {"a": gt(100, 80, ("RBC", [0, 0, 100, 80]))}
    detections = [Detection(cls="RBC", conf=0.5, box=[0.0, 0.0, 100.0, 80.0])]

    report = evaluate_detection_references(
        ground_truth, {"a": save(tmp_path, "a", detections)}, 0.5
    )

    assert report["images"][0]["status"] == "valid"
    assert report["summary"]["true_positives"] == 1


def test_no_detections_is_a_valid_empty_answer(tmp_path):
    ground_truth = {"a": gt(100, 100, ("WBC", [10, 10, 50, 50]))}

    report = evaluate_detection_references(
        ground_truth, {"a": save(tmp_path, "a", [])}, 0.5
    )

    assert report["images"][0]["status"] == "valid"
    assert report["summary"]["valid_responses_without_detections"] == 1
    assert report["summary"]["false_negatives"] == 1


def test_image_without_detection_file_is_missing(tmp_path):
    ground_truth = {
        "a": gt(100, 100, ("WBC", [10, 10, 50, 50])),
        "b": gt(100, 100, ("WBC", [10, 10, 50, 50])),
    }

    report = evaluate_detection_references(
        ground_truth, {"a": save(tmp_path, "a", [])}, 0.5
    )

    statuses = {image["image_id"]: image["status"] for image in report["images"]}
    assert statuses == {"a": "valid", "b": "missing_response"}


def test_box_outside_the_image_is_reported_not_hidden(tmp_path):
    ground_truth = {"a": gt(100, 100, ("WBC", [10, 10, 50, 50]))}
    detections = [Detection(cls="WBC", conf=0.5, box=[10.0, 10.0, 150.0, 50.0])]

    report = evaluate_detection_references(
        ground_truth, {"a": save(tmp_path, "a", detections)}, 0.5
    )

    assert report["images"][0]["status"] == "invalid_response"
    assert "outside the image" in report["images"][0]["error"]
