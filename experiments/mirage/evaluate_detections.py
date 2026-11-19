"""Evaluate detections parsed from MIRAGE text answers against human annotations.

Run from the repository root (offline, in the project environment, NOT in the
MIRAGE conda environment, which pins pydantic<2):

    uv run python -m experiments.mirage.evaluate_detections \
        --ground-truth annotations.json \
        --predictions predictions.json \
        --coordinate-format normalized_padded_square \
        --output report.json

Text answers are parsed only by the project's ``TextDetectionParser``; this
module adds matching and metrics. MIRAGE provides no detection confidence, so
there is no ranking and no AP/mAP. Must stay compatible with Python 3.10.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from mlops_workflows.components.text_detection_parsing.text_detection_parser import (
    TextDetectionParser,
)

STATUS_VALID = "valid"
STATUS_INVALID = "invalid_response"
STATUS_MISSING = "missing_response"

_COUNT_KEYS = ("true_positives", "false_positives", "false_negatives")

MATCHING_METHOD = (
    "Optimal one-to-one bipartite matching (Hungarian algorithm): eligible pairs "
    "have IoU >= threshold (and the same class in class-aware mode); the number "
    "of matched pairs is maximized first, then the sum of their IoUs. Each "
    "prediction and each annotation is used at most once. No confidence ranking "
    "is used. Replaced the greedy matching on 2026-11-18 (greedy could miss TPs)."
)
INVALID_RESPONSE_POLICY = (
    "Images with an invalid or missing response are kept in the evaluation with "
    "zero predictions: all their annotations count as false negatives. They are "
    "never excluded, so they cannot improve precision or recall."
)


def box_iou(first: list[float], second: list[float]) -> float:
    """Return the IoU of two [x1, y1, x2, y2] boxes in continuous pixels."""
    width = min(first[2], second[2]) - max(first[0], second[0])
    height = min(first[3], second[3]) - max(first[1], second[1])

    if width <= 0 or height <= 0:
        return 0.0

    intersection = width * height
    area_first = (first[2] - first[0]) * (first[3] - first[1])
    area_second = (second[2] - second[0]) * (second[3] - second[1])

    return intersection / (area_first + area_second - intersection)


def _max_weight_assignment(weights: list[list[float]]) -> list[int]:
    """Return, for each row, the column of a maximum-weight assignment.

    Hungarian algorithm (Kuhn-Munkres, O(n^2 m)) on the costs ``-weight``;
    requires ``len(weights) <= len(weights[0])``. Standard library only.
    """
    rows, cols = len(weights), len(weights[0])
    infinity = float("inf")
    u = [0.0] * (rows + 1)
    v = [0.0] * (cols + 1)
    owner = [0] * (cols + 1)
    way = [0] * (cols + 1)
    for row in range(1, rows + 1):
        owner[0] = row
        column = 0
        min_slack = [infinity] * (cols + 1)
        used = [False] * (cols + 1)
        while True:
            used[column] = True
            current_row = owner[column]
            delta, next_column = infinity, 0
            for j in range(1, cols + 1):
                if used[j]:
                    continue
                slack = -weights[current_row - 1][j - 1] - u[current_row] - v[j]
                if slack < min_slack[j]:
                    min_slack[j], way[j] = slack, column
                if min_slack[j] < delta:
                    delta, next_column = min_slack[j], j
            for j in range(cols + 1):
                if used[j]:
                    u[owner[j]] += delta
                    v[j] -= delta
                else:
                    min_slack[j] -= delta
            column = next_column
            if owner[column] == 0:
                break
        while column:
            previous = way[column]
            owner[column] = owner[previous]
            column = previous
    assignment = [-1] * rows
    for j in range(1, cols + 1):
        if owner[j]:
            assignment[owner[j] - 1] = j - 1
    return assignment


def match_detections(
    predictions: list[dict[str, object]],
    annotations: list[dict[str, object]],
    iou_threshold: float,
    class_aware: bool = True,
) -> list[tuple[int, int, float]]:
    """Return an optimal one-to-one matching as (prediction, annotation, iou).

    Eligible pairs have IoU >= ``iou_threshold`` and, if ``class_aware``, the
    same class. Among all one-to-one matchings it first maximizes the number
    of pairs (true positives) and then the sum of their IoUs: each eligible
    pair weighs ``M + iou`` with ``M`` larger than any possible number of
    pairs, so one more pair always outweighs any IoU gain. Results are sorted
    by prediction index.
    """
    eligible: dict[tuple[int, int], float] = {}
    for p_index, prediction in enumerate(predictions):
        for a_index, annotation in enumerate(annotations):
            if class_aware and prediction["cls"] != annotation["cls"]:
                continue
            iou = box_iou(prediction["box"], annotation["box"])
            if iou >= iou_threshold:
                eligible[(p_index, a_index)] = iou
    if not eligible:
        return []

    pred_ids = sorted({p for p, _ in eligible})
    ann_ids = sorted({a for _, a in eligible})
    transpose = len(pred_ids) > len(ann_ids)
    row_ids, col_ids = (ann_ids, pred_ids) if transpose else (pred_ids, ann_ids)
    big = len(row_ids) + 1

    def pair(row: int, col: int) -> tuple[int, int]:
        return (col, row) if transpose else (row, col)

    weights = [
        [
            big + eligible[pair(row, col)] if pair(row, col) in eligible else 0.0
            for col in col_ids
        ]
        for row in row_ids
    ]
    matches = []
    for row_pos, col_pos in enumerate(_max_weight_assignment(weights)):
        key = pair(row_ids[row_pos], col_ids[col_pos])
        if key in eligible:
            matches.append((key[0], key[1], eligible[key]))
    return sorted(matches)


def _ratio(numerator: int, denominator: int) -> float | None:
    """Return a ratio, or None when it is undefined (zero denominator)."""
    return numerator / denominator if denominator else None


def _counts(tp: int, fp: int, fn: int) -> dict[str, object]:
    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": _ratio(tp, tp + fp),
        "recall": _ratio(tp, tp + fn),
    }


def evaluate(
    ground_truth: dict[str, dict[str, object]],
    responses: dict[str, str | None],
    parser: TextDetectionParser,
    iou_threshold: float,
    class_aware: bool = True,
) -> dict[str, object]:
    """Evaluate text responses against annotations, keyed by image ID.

    ``ground_truth`` maps image IDs to ``{"width", "height", "objects"}`` with
    pixel boxes. ``responses`` maps image IDs to the raw answer text, or None
    when the run produced no answer. Every annotated image is evaluated.

    With ``class_aware=False`` boxes are matched regardless of class, which
    measures localization alone: TPs and FNs are counted under the annotated
    class, FPs under the predicted class, and ``confusion`` (annotated class ->
    predicted class -> count of matched pairs) shows how matched objects were
    labelled. In class-aware mode ``confusion`` is diagonal by construction.
    """
    if not 0 < iou_threshold <= 1:
        raise ValueError("The IoU threshold must be in (0, 1].")

    unknown = sorted(set(responses) - set(ground_truth))
    if unknown:
        raise ValueError(f"Responses for images without annotations: {unknown}")

    images = []
    per_class: dict[str, list[int]] = {}
    confusion: dict[str, dict[str, int]] = {}
    matched_ious = []

    for image_id in sorted(ground_truth):
        entry = ground_truth[image_id]
        annotations = entry["objects"]
        text = responses.get(image_id)
        error = None

        if image_id not in responses:
            status, predictions = STATUS_MISSING, []
            error = "No prediction entry for this image."
        elif text is None:
            status, predictions = STATUS_MISSING, []
            error = "The run produced no answer text."
        else:
            try:
                detections = parser.parse(text, entry["width"], entry["height"])
            except ValueError as exc:
                status, predictions, error = STATUS_INVALID, [], str(exc)
            else:
                status = STATUS_VALID
                predictions = [{"cls": d.cls, "box": d.box} for d in detections]

        matches = match_detections(
            predictions, annotations, iou_threshold, class_aware=class_aware
        )
        matched_predictions = {p for p, _, _ in matches}
        matched_annotations = {a for _, a, _ in matches}

        for p_index, a_index, _ in matches:
            annotated, predicted = (
                annotations[a_index]["cls"],
                predictions[p_index]["cls"],
            )
            per_class.setdefault(annotated, [0, 0, 0])[0] += 1
            row = confusion.setdefault(annotated, {})
            row[predicted] = row.get(predicted, 0) + 1

        for p_index, prediction in enumerate(predictions):
            if p_index not in matched_predictions:
                per_class.setdefault(prediction["cls"], [0, 0, 0])[1] += 1

        for a_index, annotation in enumerate(annotations):
            if a_index not in matched_annotations:
                per_class.setdefault(annotation["cls"], [0, 0, 0])[2] += 1

        matched_ious.extend(iou for _, _, iou in matches)
        tp = len(matches)
        images.append(
            {
                "image_id": image_id,
                "status": status,
                "error": error,
                "annotated_objects": len(annotations),
                "predicted_objects": len(predictions),
                **_counts(tp, len(predictions) - tp, len(annotations) - tp),
                "predictions": predictions,
                "matches": [
                    {
                        "prediction_index": p,
                        "annotation_index": a,
                        "cls": predictions[p]["cls"],
                        "annotation_cls": annotations[a]["cls"],
                        "iou": iou,
                    }
                    for p, a, iou in matches
                ],
                "unmatched_prediction_indices": [
                    i for i in range(len(predictions)) if i not in matched_predictions
                ],
                "unmatched_annotation_indices": [
                    i for i in range(len(annotations)) if i not in matched_annotations
                ],
            }
        )

    totals = [sum(image[key] for image in images) for key in _COUNT_KEYS]
    statuses = [image["status"] for image in images]

    return {
        "summary": {
            "images": len(images),
            "valid_responses": statuses.count(STATUS_VALID),
            "invalid_responses": statuses.count(STATUS_INVALID),
            "missing_responses": statuses.count(STATUS_MISSING),
            "images_without_annotations": sum(
                1 for image in images if image["annotated_objects"] == 0
            ),
            "valid_responses_without_detections": sum(
                1
                for image in images
                if image["status"] == STATUS_VALID and image["predicted_objects"] == 0
            ),
            **_counts(*totals),
            "mean_matched_iou": (
                sum(matched_ious) / len(matched_ious) if matched_ious else None
            ),
        },
        "per_class": {cls: _counts(*per_class[cls]) for cls in sorted(per_class)},
        "class_aware": class_aware,
        "confusion": {
            cls: dict(sorted(confusion[cls].items())) for cls in sorted(confusion)
        },
        "images": images,
    }


def load_ground_truth(path: Path) -> dict[str, dict[str, object]]:
    """Load and validate human annotations (pixel boxes of the original image).

    Format: ``{"images": [{"image_id", "width", "height", "objects": [{"cls",
    "box"}]}]}``. Objects are validated with ``TextDetectionParser("pixel")``,
    so annotations follow exactly the same rules as parsed predictions.
    """
    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict) or not isinstance(data.get("images"), list):
        raise TypeError("Ground truth must be an object with an 'images' list.")

    pixel_parser = TextDetectionParser("pixel")
    ground_truth = {}

    for entry in data["images"]:
        image_id = entry.get("image_id") if isinstance(entry, dict) else None

        if not isinstance(image_id, str) or not image_id:
            raise ValueError("Each annotated image needs a non-empty 'image_id'.")
        if image_id in ground_truth:
            raise ValueError(f"Duplicate image_id in ground truth: {image_id}")

        width, height = entry.get("width"), entry.get("height")

        try:
            objects = pixel_parser.parse(
                json.dumps(entry.get("objects")), width, height
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid annotations for {image_id}: {exc}") from exc

        ground_truth[image_id] = {
            "width": width,
            "height": height,
            "objects": [{"cls": o.cls, "box": o.box} for o in objects],
        }

    return ground_truth


def load_responses(
    path: Path,
    ground_truth: dict[str, dict[str, object]],
) -> tuple[dict[str, str | None], dict[str, str]]:
    """Load answers from run directories listed with explicit image IDs.

    Format: ``{"predictions": [{"image_id", "run_dir"}]}``; relative run
    directories are resolved against the manifest's folder. Each ``run.json``
    must associate the answer with exactly one image whose size matches the
    annotation, otherwise the setup is rejected. A run without ``answer.txt``
    yields None (missing response).
    """
    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict) or not isinstance(data.get("predictions"), list):
        raise TypeError("Predictions must be an object with a 'predictions' list.")

    responses: dict[str, str | None] = {}
    run_dirs: dict[str, str] = {}

    for entry in data["predictions"]:
        if not isinstance(entry, dict):
            raise TypeError("Each prediction entry must be an object.")

        image_id, run_dir = entry.get("image_id"), entry.get("run_dir")

        if not isinstance(image_id, str) or not isinstance(run_dir, str):
            raise TypeError("Each prediction needs string 'image_id' and 'run_dir'.")
        if image_id in responses:
            raise ValueError(f"Duplicate image_id in predictions: {image_id}")
        if image_id not in ground_truth:
            raise ValueError(f"No annotations for predicted image_id: {image_id}")

        directory = (path.parent / run_dir).resolve()
        run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
        images = run.get("images") or []

        if run.get("answer_image") is None or len(images) != 1:
            raise ValueError(
                f"{run_dir}: run.json does not associate the answer with exactly "
                "one image; coordinates cannot be attributed."
            )

        expected = ground_truth[image_id]
        if (images[0].get("width"), images[0].get("height")) != (
            expected["width"],
            expected["height"],
        ):
            raise ValueError(
                f"{run_dir}: image size in run.json differs from the annotation "
                f"of {image_id}; wrong association or different image."
            )

        answer_path = directory / "answer.txt"
        responses[image_id] = (
            answer_path.read_text(encoding="utf-8") if answer_path.is_file() else None
        )
        run_dirs[image_id] = str(directory)

    return responses, run_dirs


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ground-truth", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument(
        "--coordinate-format",
        required=True,
        help="pixel, normalized_image or normalized_padded_square (no default).",
    )
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arg_parser = build_arg_parser()
    args = arg_parser.parse_args(argv)

    try:
        text_parser = TextDetectionParser(args.coordinate_format)
        ground_truth = load_ground_truth(args.ground_truth)
        responses, run_dirs = load_responses(args.predictions, ground_truth)
        report = evaluate(ground_truth, responses, text_parser, args.iou_threshold)
    except (OSError, UnicodeError, TypeError, ValueError) as exc:
        arg_parser.error(str(exc))

    report = {
        "parameters": {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "ground_truth": str(args.ground_truth.resolve()),
            "predictions": str(args.predictions.resolve()),
            "run_dirs": run_dirs,
            "coordinate_format": args.coordinate_format,
            "iou_threshold": args.iou_threshold,
            "matching_method": MATCHING_METHOD,
            "invalid_response_policy": INVALID_RESPONSE_POLICY,
            "confidence": "Not available; AP/mAP are not computed.",
            "python": sys.version,
        },
        **report,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    summary = report["summary"]
    print(
        f"Images: {summary['images']} (invalid: {summary['invalid_responses']}, "
        f"missing: {summary['missing_responses']})"
    )
    print(
        f"TP={summary['true_positives']} FP={summary['false_positives']} "
        f"FN={summary['false_negatives']} precision={summary['precision']} "
        f"recall={summary['recall']}"
    )
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
