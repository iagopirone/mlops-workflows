"""Test the Qwen3-VL answer adapter and renderer without loading the model."""

import hashlib
import json

import cv2
import numpy as np
import pytest

from experiments.qwen3vl.qwen_detections import (
    QwenOutputError,
    coordinate_evidence,
    extract_json,
    qwen_to_detections,
)
from experiments.qwen3vl.render import render

W, H = 640, 480


def answer(*items, fence=False):
    text = json.dumps([{"bbox_2d": b, "label": label} for b, label in items])
    return f"```json\n{text}\n```" if fence else text


def test_relative_1000_is_scaled_per_axis():
    result = qwen_to_detections(
        answer(([312, 451, 675, 900], "white blood cell")), "relative_1000", W, H
    )

    assert result[0].box == pytest.approx([199.68, 216.48, 432.0, 432.0])
    assert result[0].cls == "white blood cell"
    assert result[0].conf is None


def test_pixel_convention_keeps_values():
    result = qwen_to_detections(answer(([200, 216, 432, 432], "cell")), "pixel", W, H)

    assert result[0].box == [200.0, 216.0, 432.0, 432.0]


def test_single_json_fence_is_accepted():
    text = answer(([0, 0, 10, 10], "platelet"), fence=True)

    assert len(qwen_to_detections(text, "relative_1000", W, H)) == 1


def test_empty_array_is_valid():
    assert qwen_to_detections("[]", "relative_1000", W, H) == []


def test_labels_are_not_mapped():
    result = qwen_to_detections(answer(([0, 0, 10, 10], "RBC")), "relative_1000", W, H)

    assert result[0].cls == "RBC"


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("There is one white blood cell in the center.", "not JSON"),
        ("Here: ```json\n[]\n```", "not JSON"),
        ('{"bbox_2d": [0, 0, 1, 1], "label": "x"}', "JSON array"),
        ('[{"bbox_2d": [0, 0, 1, 1]}]', "exactly 'bbox_2d' and 'label'"),
        ('[{"bbox_2d": [0, 0, 1, 1], "label": "x", "conf": 0.9}]', "exactly"),
        ('[{"bbox_2d": [0, 0, 1], "label": "x"}]', "four finite"),
        ('[{"bbox_2d": [0, 0, true, 1], "label": "x"}]', "four finite"),
        ('[{"bbox_2d": [5, 0, 1, 1], "label": "x"}]', "x1 < x2"),
        ('[{"bbox_2d": [0, 0, 1001, 10], "label": "x"}]', "outside"),
        ('[{"bbox_2d": [-1, 0, 10, 10], "label": "x"}]', "outside"),
        ('[{"bbox_2d": [0, 0, 1, 1], "label": " "}]', "label"),
    ],
)
def test_invalid_answers_are_rejected_whole(text, message):
    with pytest.raises(QwenOutputError, match=message):
        qwen_to_detections(text, "relative_1000", W, H)


def test_pixel_range_uses_image_size():
    with pytest.raises(QwenOutputError, match="outside"):
        qwen_to_detections(answer(([0, 0, 700, 10], "x")), "pixel", W, H)


def test_unknown_convention():
    with pytest.raises(ValueError, match="Unsupported convention"):
        qwen_to_detections("[]", "normalized", W, H)


def test_extract_json_reads_the_fence_content():
    assert extract_json("```json\n[1, 2]\n```") == [1, 2]


@pytest.mark.parametrize(
    ("boxes", "pixel_out", "relative_out"),
    [
        ([[312, 451, 675, 900]], True, False),  # y 900 > 480: not pixels
        ([[200, 216, 432, 432]], False, False),  # ambiguous
        ([[200, 216, 1432, 432]], True, True),
    ],
)
def test_coordinate_evidence(boxes, pixel_out, relative_out):
    evidence = coordinate_evidence(answer(*[(b, "x") for b in boxes]), W, H)

    assert evidence["rules_out_pixel"] is pixel_out
    assert evidence["rules_out_relative_1000"] is relative_out


def test_coordinate_evidence_without_json():
    assert coordinate_evidence("no boxes here", W, H) == {"parsed": False, "boxes": 0}


def test_coordinate_evidence_reads_boxes_in_broken_json():
    broken = '[{"bbox_2d": [775, 0, 944, 255], "label": "x"}, {"bbox_2d": 355, 0'

    evidence = coordinate_evidence(broken, W, H)

    assert evidence["parsed"] is False
    assert evidence["boxes"] == 1
    assert evidence["rules_out_pixel"] is True


def write_run(tmp_path, prompts):
    image = tmp_path / "img.png"
    assert cv2.imwrite(str(image), np.zeros((H, W, 3), dtype=np.uint8))
    entries = []
    for name, returncode, text in prompts:
        (tmp_path / f"{name}.stdout.txt").write_text(text, encoding="utf-8")
        entries.append({"name": name, "prompt": name, "returncode": returncode,
                        "stdout_file": f"{name}.stdout.txt"})  # fmt: skip
    run = {
        "image": {"path": str(image), "sha256": hashlib.sha256(image.read_bytes()).hexdigest()},
        "prompts": entries,
    }  # fmt: skip
    (tmp_path / "run.json").write_text(json.dumps(run))
    return tmp_path


def test_render_statuses_and_outputs(tmp_path):
    run_dir = write_run(
        tmp_path,
        [
            ("describe", 0, "A blood smear with many red cells."),
            ("ground_wbc", 0, answer(([312, 451, 675, 900], "white blood cell"))),
            ("ground_bad", 0, '[{"bbox_2d": [5, 0, 1, 1], "label": "x"}]'),
            ("ground_cut", 0, '```json\n[{"bbox_2d": [1, 2, 3, 4], "label": "x"},'),
            ("ground_empty", 0, "[]"),
            ("ground_fail", 1, ""),
        ],
    )
    before = (run_dir / "ground_wbc.stdout.txt").read_bytes()

    summary = render(run_dir, "relative_1000")

    statuses = {p["name"]: p["status"] for p in summary["prompts"]}
    assert statuses == {
        "describe": "text_only",
        "ground_wbc": "detections",
        "ground_bad": "invalid_output",
        "ground_cut": "invalid_output",
        "ground_empty": "no_detections",
        "ground_fail": "error",
    }
    wbc = next(p for p in summary["prompts"] if p["name"] == "ground_wbc")
    assert wbc["coordinate_evidence"]["rules_out_pixel"] is True
    assert (run_dir / wbc["annotated_image"]).is_file()
    saved = json.loads((run_dir / wbc["detections_file"]).read_text())
    assert saved[0]["conf"] is None
    assert (run_dir / "ground_wbc.stdout.txt").read_bytes() == before


def test_render_rejects_a_different_image(tmp_path):
    run_dir = write_run(tmp_path, [])
    cv2.imwrite(str(tmp_path / "img.png"), np.full((H, W, 3), 255, np.uint8))

    with pytest.raises(ValueError, match="SHA-256"):
        render(run_dir, "relative_1000")
