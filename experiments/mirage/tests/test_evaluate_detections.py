"""Offline tests for the detection evaluator, using synthetic data only.

Run from the repository root (``python -m pytest``) so that ``mlops_workflows``
and ``experiments`` are importable.
"""

from __future__ import annotations

import itertools
import json
import random
import subprocess
import sys
from pathlib import Path

import pytest

from experiments.mirage import evaluate_detections as ev
from mlops_workflows.components.text_detection_parsing.text_detection_parser import (
    TextDetectionParser,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def gt(width: int, height: int, *objects: tuple[str, list[float]]) -> dict:
    """Build one ground-truth entry with pixel boxes."""
    return {
        "width": width,
        "height": height,
        "objects": [{"cls": cls, "box": box} for cls, box in objects],
    }


def answer(*objects: tuple[str, list[float]]) -> str:
    """Build a JSON text answer in the parser's format."""
    return json.dumps([{"cls": cls, "box": box} for cls, box in objects])


def run_eval(ground_truth, responses, coordinate_format="pixel", threshold=0.5):
    return ev.evaluate(
        ground_truth, responses, TextDetectionParser(coordinate_format), threshold
    )


# IoU


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ([0, 0, 10, 10], [0, 0, 10, 10], 1.0),
        ([0, 0, 10, 10], [20, 20, 30, 30], 0.0),
        ([0, 0, 10, 10], [10, 0, 20, 10], 0.0),  # Touching edges only.
        ([0, 0, 10, 10], [5, 0, 15, 10], 50 / 150),
        ([0, 0, 10, 10], [0, 0, 5, 10], 0.5),  # Contained.
        ([0.5, 0.5, 2.5, 2.5], [1.5, 1.5, 3.5, 3.5], 1 / 7),
    ],
)
def test_box_iou(first, second, expected):
    assert ev.box_iou(first, second) == pytest.approx(expected)
    assert ev.box_iou(second, first) == pytest.approx(expected)


# Matching


def test_match_is_one_to_one_and_prefers_highest_iou():
    annotations = [{"cls": "a", "box": [0, 0, 10, 10]}]
    predictions = [
        {"cls": "a", "box": [1, 0, 11, 10]},  # IoU 9/11
        {"cls": "a", "box": [0, 0, 10, 10]},  # IoU 1
        {"cls": "a", "box": [0, 0, 10, 9]},  # IoU 0.9
    ]

    matches = ev.match_detections(predictions, annotations, 0.5)

    assert matches == [(1, 0, 1.0)]


def test_one_prediction_cannot_match_two_annotations():
    annotations = [
        {"cls": "a", "box": [0, 0, 10, 10]},
        {"cls": "a", "box": [0, 0, 10, 10]},
    ]
    predictions = [{"cls": "a", "box": [0, 0, 10, 10]}]

    assert len(ev.match_detections(predictions, annotations, 0.5)) == 1


def test_match_requires_same_class():
    annotations = [{"cls": "WBC", "box": [0, 0, 10, 10]}]
    predictions = [{"cls": "RBC", "box": [0, 0, 10, 10]}]

    assert ev.match_detections(predictions, annotations, 0.5) == []


def test_match_threshold_is_inclusive_and_configurable():
    annotations = [{"cls": "a", "box": [0, 0, 10, 10]}]
    predictions = [{"cls": "a", "box": [0, 0, 5, 10]}]  # IoU exactly 0.5

    assert len(ev.match_detections(predictions, annotations, 0.5)) == 1
    assert ev.match_detections(predictions, annotations, 0.51) == []


# Evaluation


def test_perfect_prediction():
    report = run_eval(
        {"img": gt(100, 100, ("WBC", [10, 10, 50, 50]))},
        {"img": answer(("WBC", [10, 10, 50, 50]))},
    )

    summary = report["summary"]
    assert summary["true_positives"] == 1
    assert summary["false_positives"] == 0
    assert summary["false_negatives"] == 0
    assert summary["precision"] == 1.0
    assert summary["recall"] == 1.0
    assert summary["mean_matched_iou"] == 1.0
    assert report["images"][0]["status"] == ev.STATUS_VALID


def test_no_overlap_counts_one_false_positive_and_one_false_negative():
    report = run_eval(
        {"img": gt(100, 100, ("WBC", [0, 0, 10, 10]))},
        {"img": answer(("WBC", [50, 50, 60, 60]))},
    )

    summary = report["summary"]
    assert (summary["true_positives"], summary["false_positives"]) == (0, 1)
    assert summary["false_negatives"] == 1
    assert summary["precision"] == 0.0
    assert summary["recall"] == 0.0
    assert summary["mean_matched_iou"] is None


def test_partial_overlap_depends_on_threshold():
    ground_truth = {"img": gt(100, 100, ("a", [0, 0, 10, 10]))}
    responses = {"img": answer(("a", [5, 0, 15, 10]))}  # IoU 1/3

    assert (
        run_eval(ground_truth, responses, threshold=0.5)["summary"]["true_positives"]
        == 0
    )
    report = run_eval(ground_truth, responses, threshold=0.3)
    assert report["summary"]["true_positives"] == 1
    assert report["summary"]["mean_matched_iou"] == pytest.approx(1 / 3)


def test_different_classes_are_counted_per_class():
    report = run_eval(
        {"img": gt(100, 100, ("WBC", [10, 10, 50, 50]))},
        {"img": answer(("RBC", [10, 10, 50, 50]))},
    )

    assert report["summary"]["true_positives"] == 0
    assert report["per_class"]["RBC"]["false_positives"] == 1
    assert report["per_class"]["RBC"]["recall"] is None
    assert report["per_class"]["WBC"]["false_negatives"] == 1
    assert report["per_class"]["WBC"]["precision"] is None


def test_multiple_predictions_for_one_object():
    report = run_eval(
        {"img": gt(100, 100, ("WBC", [10, 10, 50, 50]))},
        {
            "img": answer(
                ("WBC", [10, 10, 50, 50]),
                ("WBC", [11, 11, 50, 50]),
                ("WBC", [10, 10, 49, 49]),
            )
        },
    )

    image = report["images"][0]
    assert (image["true_positives"], image["false_positives"]) == (1, 2)
    assert image["false_negatives"] == 0
    assert image["matches"][0]["prediction_index"] == 0
    assert image["unmatched_prediction_indices"] == [1, 2]
    assert report["summary"]["precision"] == pytest.approx(1 / 3)


def test_valid_empty_answer_with_annotations():
    report = run_eval(
        {"img": gt(100, 100, ("WBC", [10, 10, 50, 50]))},
        {"img": "[]"},
    )

    image = report["images"][0]
    assert image["status"] == ev.STATUS_VALID
    assert image["false_negatives"] == 1
    assert image["precision"] is None
    assert image["recall"] == 0.0
    assert report["summary"]["valid_responses_without_detections"] == 1


def test_image_without_annotations():
    report = run_eval(
        {"empty": gt(100, 100), "busy": gt(100, 100)},
        {"empty": "[]", "busy": answer(("WBC", [10, 10, 50, 50]))},
    )

    images = {image["image_id"]: image for image in report["images"]}
    assert images["empty"]["false_positives"] == 0
    assert images["empty"]["precision"] is None
    assert images["empty"]["recall"] is None
    assert images["busy"]["false_positives"] == 1
    assert images["busy"]["recall"] is None
    assert report["summary"]["images_without_annotations"] == 2
    assert report["summary"]["recall"] is None


@pytest.mark.parametrize(
    "text",
    [
        "I can see one white blood cell.",
        '[{"cls": "WBC", "box": [10, 10, 50, 50]',
        '[{"cls": "WBC", "box": [10, 10, 500, 50]}]',  # Outside the image.
        '[{"cls": "WBC", "box": [50, 10, 10, 50]}]',  # Unordered.
        '[{"cls": "WBC", "box": [10, 10, 50, 50], "conf": 0.9}]',
    ],
)
def test_invalid_answers_are_kept_as_false_negatives(text):
    ground_truth = {
        "bad": gt(100, 100, ("WBC", [10, 10, 50, 50])),
        "good": gt(100, 100, ("WBC", [10, 10, 50, 50])),
    }

    report = run_eval(
        ground_truth, {"bad": text, "good": answer(("WBC", [10, 10, 50, 50]))}
    )

    images = {image["image_id"]: image for image in report["images"]}
    assert images["bad"]["status"] == ev.STATUS_INVALID
    assert images["bad"]["error"]
    assert images["bad"]["false_negatives"] == 1
    assert report["summary"]["invalid_responses"] == 1
    # Excluding the invalid image would have produced recall 1.0.
    assert report["summary"]["recall"] == 0.5
    assert report["summary"]["precision"] == 1.0


def test_missing_responses_are_kept_with_reason():
    ground_truth = {
        "no_entry": gt(100, 100, ("a", [0, 0, 10, 10])),
        "no_answer": gt(100, 100, ("a", [0, 0, 10, 10])),
    }

    report = run_eval(ground_truth, {"no_answer": None})

    images = {image["image_id"]: image for image in report["images"]}
    assert images["no_entry"]["status"] == ev.STATUS_MISSING
    assert "No prediction entry" in images["no_entry"]["error"]
    assert "no answer text" in images["no_answer"]["error"]
    assert report["summary"]["missing_responses"] == 2
    assert report["summary"]["false_negatives"] == 2


def test_responses_are_matched_by_image_id_not_order():
    ground_truth = {
        "a": gt(100, 100, ("x", [0, 0, 10, 10])),
        "b": gt(100, 100, ("x", [50, 50, 90, 90])),
    }
    responses = {
        "b": answer(("x", [50, 50, 90, 90])),
        "a": answer(("x", [0, 0, 10, 10])),
    }

    assert run_eval(ground_truth, responses)["summary"]["true_positives"] == 2


def test_rejects_responses_for_unknown_images():
    with pytest.raises(ValueError, match="without annotations"):
        run_eval({"a": gt(10, 10)}, {"a": "[]", "z": "[]"})


@pytest.mark.parametrize("threshold", [0, -0.1, 1.01])
def test_rejects_invalid_threshold(threshold):
    with pytest.raises(ValueError, match="IoU threshold"):
        run_eval({"a": gt(10, 10)}, {"a": "[]"}, threshold=threshold)


@pytest.mark.parametrize(
    ("coordinate_format", "box"),
    [
        ("pixel", [10, 10, 50, 40]),
        ("normalized_image", [0.1, 0.2, 0.5, 0.8]),
        # Landscape 100x50: square side 100, vertical offset 25.
        ("normalized_padded_square", [0.1, 0.35, 0.5, 0.65]),
    ],
)
def test_supported_coordinate_formats(coordinate_format, box):
    report = run_eval(
        {"img": gt(100, 50, ("WBC", [10, 10, 50, 40]))},
        {"img": answer(("WBC", box))},
        coordinate_format=coordinate_format,
    )

    assert report["summary"]["true_positives"] == 1
    assert report["images"][0]["predictions"][0]["box"] == pytest.approx(
        [10, 10, 50, 40]
    )


# Loading files


def write_json(path: Path, data: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def write_run(directory: Path, width: int, height: int, text: str | None) -> None:
    """Write a run directory shaped like run_poc.py output."""
    write_json(
        directory / "run.json",
        {
            "answer_image": str(directory / "image.png"),
            "images": [{"path": "image.png", "width": width, "height": height}],
        },
    )
    if text is not None:
        (directory / "answer.txt").write_text(text, encoding="utf-8")


def gt_file(tmp_path: Path, images: list[dict]) -> Path:
    return write_json(tmp_path / "gt.json", {"images": images})


def test_load_ground_truth_validates_with_pixel_parser(tmp_path):
    path = gt_file(
        tmp_path,
        [
            {
                "image_id": "a",
                "width": 100,
                "height": 50,
                "objects": [{"cls": "WBC", "box": [1, 2, 30, 40]}],
            },
            {"image_id": "b", "width": 10, "height": 10, "objects": []},
        ],
    )

    loaded = ev.load_ground_truth(path)

    assert loaded["a"]["objects"] == [{"cls": "WBC", "box": [1.0, 2.0, 30.0, 40.0]}]
    assert loaded["b"]["objects"] == []


@pytest.mark.parametrize(
    "images",
    [
        [{"image_id": "a", "width": 10, "height": 10, "objects": []}] * 2,
        [{"image_id": "", "width": 10, "height": 10, "objects": []}],
        [{"image_id": "a", "width": 10, "height": 10}],
        [{"image_id": "a", "width": True, "height": 10, "objects": []}],
        [
            {
                "image_id": "a",
                "width": 10,
                "height": 10,
                "objects": [{"cls": "x", "box": [0, 0, 11, 5]}],
            }
        ],
    ],
)
def test_load_ground_truth_rejects_invalid_files(tmp_path, images):
    with pytest.raises(ValueError):
        ev.load_ground_truth(gt_file(tmp_path, images))


def test_load_ground_truth_rejects_wrong_structure(tmp_path):
    with pytest.raises(TypeError):
        ev.load_ground_truth(write_json(tmp_path / "gt.json", [{"image_id": "a"}]))


def test_load_responses_reads_runs_relative_to_manifest(tmp_path):
    ground_truth = {"a": gt(64, 32), "b": gt(64, 32)}
    write_run(tmp_path / "runs" / "run_a", 64, 32, "[]")
    write_run(tmp_path / "runs" / "run_b", 64, 32, None)
    manifest = write_json(
        tmp_path / "predictions.json",
        {
            "predictions": [
                {"image_id": "a", "run_dir": "runs/run_a"},
                {"image_id": "b", "run_dir": "runs/run_b"},
            ]
        },
    )

    responses, run_dirs = ev.load_responses(manifest, ground_truth)

    assert responses == {"a": "[]", "b": None}
    assert run_dirs["a"] == str((tmp_path / "runs" / "run_a").resolve())


def test_load_responses_rejects_size_mismatch(tmp_path):
    write_run(tmp_path / "run", 64, 32, "[]")
    manifest = write_json(
        tmp_path / "p.json", {"predictions": [{"image_id": "a", "run_dir": "run"}]}
    )

    with pytest.raises(ValueError, match="differs from the annotation"):
        ev.load_responses(manifest, {"a": gt(32, 64)})


def test_load_responses_rejects_ambiguous_multi_image_run(tmp_path):
    write_json(
        tmp_path / "run" / "run.json",
        {
            "answer_image": None,
            "images": [
                {"path": "a.png", "width": 10, "height": 10},
                {"path": "b.png", "width": 10, "height": 10},
            ],
        },
    )
    manifest = write_json(
        tmp_path / "p.json", {"predictions": [{"image_id": "a", "run_dir": "run"}]}
    )

    with pytest.raises(ValueError, match="exactly one image"):
        ev.load_responses(manifest, {"a": gt(10, 10)})


@pytest.mark.parametrize(
    ("entries", "message"),
    [
        (
            [{"image_id": "a", "run_dir": "run"}, {"image_id": "a", "run_dir": "run"}],
            "Duplicate image_id",
        ),
        ([{"image_id": "zzz", "run_dir": "run"}], "No annotations"),
    ],
)
def test_load_responses_rejects_bad_identifiers(tmp_path, entries, message):
    write_run(tmp_path / "run", 10, 10, "[]")
    manifest = write_json(tmp_path / "p.json", {"predictions": entries})

    with pytest.raises(ValueError, match=message):
        ev.load_responses(manifest, {"a": gt(10, 10)})


# Command line


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "experiments.mirage.evaluate_detections", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_writes_report_with_parameters(tmp_path):
    gt_path = gt_file(
        tmp_path,
        [
            {
                "image_id": "blood",
                "width": 100,
                "height": 50,
                "objects": [{"cls": "WBC", "box": [10, 10, 50, 40]}],
            },
            {
                "image_id": "broken",
                "width": 100,
                "height": 50,
                "objects": [{"cls": "WBC", "box": [10, 10, 50, 40]}],
            },
        ],
    )
    write_run(tmp_path / "run_blood", 100, 50, answer(("WBC", [0.1, 0.35, 0.5, 0.65])))
    write_run(tmp_path / "run_broken", 100, 50, "Not JSON at all.")
    manifest = write_json(
        tmp_path / "predictions.json",
        {
            "predictions": [
                {"image_id": "blood", "run_dir": "run_blood"},
                {"image_id": "broken", "run_dir": "run_broken"},
            ]
        },
    )
    output = tmp_path / "report" / "report.json"

    result = run_cli(
        "--ground-truth",
        str(gt_path),
        "--predictions",
        str(manifest),
        "--coordinate-format",
        "normalized_padded_square",
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["parameters"]["iou_threshold"] == 0.5
    assert report["parameters"]["coordinate_format"] == "normalized_padded_square"
    assert "AP/mAP are not computed" in report["parameters"]["confidence"]
    assert "never excluded" in report["parameters"]["invalid_response_policy"]
    assert report["summary"]["true_positives"] == 1
    assert report["summary"]["invalid_responses"] == 1
    assert report["summary"]["recall"] == 0.5


def test_cli_requires_explicit_coordinate_format(tmp_path):
    result = run_cli(
        "--ground-truth", "gt.json", "--predictions", "p.json", "--output", "r.json"
    )

    assert result.returncode != 0
    assert "--coordinate-format" in result.stderr


def test_cli_reports_setup_errors_without_writing(tmp_path):
    output = tmp_path / "report.json"

    result = run_cli(
        "--ground-truth",
        str(tmp_path / "missing.json"),
        "--predictions",
        str(tmp_path / "missing.json"),
        "--coordinate-format",
        "pixel",
        "--output",
        str(output),
    )

    assert result.returncode != 0
    assert not output.exists()


def test_end_to_end_with_run_poc_output(tmp_path):
    """run_poc.py (fake demo, no model) -> evaluator, using real run.json/answer.txt."""
    from experiments.mirage import run_poc

    repo = tmp_path / "official"
    repo.mkdir()
    (repo / "demo.py").write_text(
        "import argparse, os\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--model-path'); p.add_argument('--image-folder')\n"
        "p.add_argument('--prompt'); p.add_argument('--max-num-retrievals')\n"
        "a = p.parse_args()\n"
        "paths = [os.path.join(a.image_folder, n) for n in os.listdir(a.image_folder)]\n"
        "print('---Input---'); print('Prompt:', a.prompt); print('Images:', paths)\n"
        "print('---Output---')\n"
        'print(\'Text Output:\', \'[{"cls": "WBC", "box": [0.1, 0.35, 0.5, 0.65]}]\')\n'
        "print('Retrieval Image:', paths)\n",
        encoding="utf-8",
    )
    images = tmp_path / "images"
    images.mkdir()
    png = _png(100, 50)
    (images / "blood.png").write_bytes(png)
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("Locate the white blood cell.", encoding="utf-8")
    model = tmp_path / "mirage-checkpoint"
    model.mkdir()

    exit_code = run_poc.main(
        [
            "--official-repo",
            str(repo),
            "--image-folder",
            str(images),
            "--prompt-file",
            str(prompt),
            "--model-path",
            str(model),
            "--output-dir",
            str(tmp_path / "runs" / "blood"),
            "--execute",
        ]
    )
    assert exit_code == 0

    gt_path = gt_file(
        tmp_path,
        [
            {
                "image_id": "blood",
                "width": 100,
                "height": 50,
                "objects": [{"cls": "WBC", "box": [10, 10, 50, 40]}],
            }
        ],
    )
    manifest = write_json(
        tmp_path / "predictions.json",
        {"predictions": [{"image_id": "blood", "run_dir": "runs/blood"}]},
    )
    responses, _ = ev.load_responses(manifest, ev.load_ground_truth(gt_path))
    report = run_eval(
        ev.load_ground_truth(gt_path),
        responses,
        coordinate_format="normalized_padded_square",
    )

    assert report["summary"]["true_positives"] == 1
    assert report["summary"]["mean_matched_iou"] == pytest.approx(1.0)


def _png(width: int, height: int) -> bytes:
    """Build a minimal PNG header recognized by run_poc.read_image_info."""
    import struct
    import zlib

    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IEND", b"")


# Optimal matching (replaced the greedy matching on 2026-11-18)


def greedy_reference(predictions, annotations, threshold):
    """The previous greedy matching, kept here only to show the difference."""
    candidates = sorted(
        (-ev.box_iou(p["box"], a["box"]), pi, ai)
        for pi, p in enumerate(predictions)
        for ai, a in enumerate(annotations)
        if p["cls"] == a["cls"] and ev.box_iou(p["box"], a["box"]) >= threshold
    )
    used_p, used_a, matches = set(), set(), []
    for neg, pi, ai in candidates:
        if pi not in used_p and ai not in used_a:
            used_p.add(pi)
            used_a.add(ai)
            matches.append((pi, ai, -neg))
    return matches


# Greedy takes P0-A0 (IoU 0.905) and stops at 1 TP; P0-A1 + P1-A0 gives 2 TP.
COUNTER_ANNOTATIONS = [
    {"cls": "RBC", "box": [5, 0, 15, 10]},
    {"cls": "RBC", "box": [7, 0, 17, 10]},
]
COUNTER_PREDICTIONS = [
    {"cls": "RBC", "box": [5.5, 0, 15.5, 10]},
    {"cls": "RBC", "box": [2, 0, 12, 10]},
]


def test_optimal_matching_finds_more_true_positives_than_greedy():
    greedy = greedy_reference(COUNTER_PREDICTIONS, COUNTER_ANNOTATIONS, 0.5)
    optimal = ev.match_detections(COUNTER_PREDICTIONS, COUNTER_ANNOTATIONS, 0.5)

    assert [(p, a) for p, a, _ in greedy] == [(0, 0)]
    assert [(p, a) for p, a, _ in optimal] == [(0, 1), (1, 0)]


def test_evaluation_counts_the_extra_true_positive():
    entry = {"width": 20, "height": 10, "objects": COUNTER_ANNOTATIONS}
    text = json.dumps(COUNTER_PREDICTIONS)

    report = ev.evaluate(
        {"img": entry}, {"img": text}, TextDetectionParser("pixel"), 0.5
    )

    assert report["summary"]["true_positives"] == 2
    assert report["summary"]["false_negatives"] == 0


def test_same_count_prefers_the_larger_iou_sum():
    annotations = [
        {"cls": "a", "box": [0, 0, 10, 10]},
        {"cls": "a", "box": [20, 0, 30, 10]},
    ]
    predictions = [
        {"cls": "a", "box": [0, 0, 10, 10]},
        {"cls": "a", "box": [21, 0, 30, 10]},
    ]

    matches = ev.match_detections(predictions, annotations, 0.5)

    assert [(p, a) for p, a, _ in matches] == [(0, 0), (1, 1)]


def brute_force(predictions, annotations, threshold, class_aware=True):
    """Best (pairs, IoU sum) over every subset of eligible pairs that is one-to-one."""
    edges = [
        (pi, ai, ev.box_iou(p["box"], a["box"]))
        for pi, p in enumerate(predictions)
        for ai, a in enumerate(annotations)
        if (not class_aware or p["cls"] == a["cls"])
        and ev.box_iou(p["box"], a["box"]) >= threshold
    ]
    best = (0, 0.0)
    for size in range(1, len(edges) + 1):
        for chosen in itertools.combinations(edges, size):
            if (
                len({e[0] for e in chosen}) == size
                and len({e[1] for e in chosen}) == size
            ):
                best = max(best, (size, round(sum(e[2] for e in chosen), 9)))
    return best


@pytest.mark.parametrize("seed", range(40))
@pytest.mark.parametrize("class_aware", [True, False])
def test_matching_is_optimal_on_random_cases(seed, class_aware):
    rng = random.Random(seed)

    def box():
        x, y = rng.uniform(0, 20), rng.uniform(0, 20)
        return {
            "cls": rng.choice("ab"),
            "box": [x, y, x + rng.uniform(4, 9), y + rng.uniform(4, 9)],
        }

    predictions = [box() for _ in range(rng.randint(1, 4))]
    annotations = [box() for _ in range(rng.randint(1, 4))]

    matches = ev.match_detections(
        predictions, annotations, 0.3, class_aware=class_aware
    )

    assert len({p for p, _, _ in matches}) == len(matches)
    assert len({a for _, a, _ in matches}) == len(matches)
    expected_pairs, expected_sum = brute_force(
        predictions, annotations, 0.3, class_aware
    )
    assert len(matches) == expected_pairs
    assert sum(iou for _, _, iou in matches) == pytest.approx(expected_sum)


def test_class_agnostic_matching_separates_localization_from_labels():
    entry = {
        "width": 100,
        "height": 100,
        "objects": [
            {"cls": "WBC", "box": [0, 0, 20, 20]},
            {"cls": "RBC", "box": [50, 50, 70, 70]},
        ],
    }
    text = json.dumps(
        [
            {"cls": "RBC", "box": [0, 0, 20, 20]},  # right place, wrong label
            {"cls": "RBC", "box": [50, 50, 70, 70]},  # right place, right label
            {"cls": "Platelets", "box": [80, 80, 90, 90]},  # nothing there
        ]
    )
    parser = TextDetectionParser("pixel")

    aware = ev.evaluate({"img": entry}, {"img": text}, parser, 0.5)
    agnostic = ev.evaluate(
        {"img": entry}, {"img": text}, parser, 0.5, class_aware=False
    )

    assert aware["summary"]["true_positives"] == 1
    assert agnostic["summary"]["true_positives"] == 2
    assert agnostic["summary"]["false_positives"] == 1
    assert agnostic["confusion"] == {"RBC": {"RBC": 1}, "WBC": {"RBC": 1}}
    assert agnostic["per_class"]["WBC"]["true_positives"] == 1
    assert agnostic["per_class"]["Platelets"]["false_positives"] == 1
    assert aware["confusion"] == {"RBC": {"RBC": 1}}
    assert agnostic["class_aware"] is False
    match = agnostic["images"][0]["matches"][0]
    assert (match["cls"], match["annotation_cls"]) == ("RBC", "WBC")
