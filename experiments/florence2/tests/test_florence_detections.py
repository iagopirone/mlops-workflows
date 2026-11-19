"""Test the Florence-2 output adapter and renderer without loading the model."""

import hashlib
import json

import cv2
import numpy as np
import pytest

from experiments.florence2.florence_detections import (
    FlorenceOutputError,
    area_fraction,
    class_source,
    florence_to_detections,
)
from experiments.florence2.render import render

OD = "<OD>"
GROUNDING = "<CAPTION_TO_PHRASE_GROUNDING>"


def parsed(task, boxes, labels):
    return {task: {"bboxes": boxes, "labels": labels}}


def test_boxes_are_copied_without_changes_and_without_confidence():
    result = florence_to_detections(
        parsed(OD, [[0.32, 0.24, 639.04, 479.28]], ["jellyfish"]), OD, 640, 480
    )

    assert len(result) == 1
    assert result[0].cls == "jellyfish"
    assert result[0].box == [0.32, 0.24, 639.04, 479.28]
    assert result[0].conf is None


def test_empty_list_is_a_valid_answer():
    assert florence_to_detections(parsed(OD, [], []), OD, 640, 480) == []


def test_grounding_empty_label_uses_the_prompt_phrase():
    result = florence_to_detections(
        parsed(GROUNDING, [[1, 2, 30, 40]], [""]), GROUNDING, 640, 480, "platelets"
    )

    assert result[0].cls == "platelets"
    assert class_source(GROUNDING) == "prompt"
    assert class_source(OD) == "model"


def test_labels_are_not_mapped_to_project_classes():
    result = florence_to_detections(
        parsed(OD, [[1, 2, 30, 40]], ["blood cell"]), OD, 640, 480
    )

    assert result[0].cls == "blood cell"


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ({"<OCR>": {}}, "exactly the key"),
        ({OD: {"bboxes": []}}, "'bboxes' and 'labels'"),
        (parsed(OD, [[1, 2, 3, 4]], []), "cannot pair"),
        (parsed(OD, [[1, 2, 3]], ["a"]), "four finite"),
        (parsed(OD, [[1, 2, 3, float("nan")]], ["a"]), "four finite"),
        (parsed(OD, [[1, 2, True, 4]], ["a"]), "four finite"),
        (parsed(OD, [[5, 2, 3, 4]], ["a"]), "x1 < x2"),
        (parsed(OD, [[1, 2, 641, 4]], ["a"]), "outside"),
        (parsed(OD, [[-1, 2, 3, 4]], ["a"]), "outside"),
        (parsed(OD, [[1, 2, 3, 4]], [None]), "not text"),
        (parsed(OD, [[1, 2, 3, 4]], ["  "]), "empty"),
    ],
)
def test_invalid_outputs_are_rejected_whole(value, message):
    with pytest.raises(FlorenceOutputError, match=message):
        florence_to_detections(value, OD, 640, 480)


def test_unsupported_task():
    with pytest.raises(ValueError, match="Unsupported task"):
        florence_to_detections({"<OCR>": "text"}, "<OCR>", 640, 480)


def test_area_fraction():
    assert area_fraction([0, 0, 640, 480], 640, 480) == 1.0
    assert area_fraction([0, 0, 320, 240], 640, 480) == 0.25


def write_run(tmp_path, tasks, width=80, height=60):
    image = tmp_path / "img.png"
    assert cv2.imwrite(str(image), np.zeros((height, width, 3), dtype=np.uint8))
    run = {
        "image": {
            "path": str(image),
            "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
            "width": width,
            "height": height,
        },
        "tasks": tasks,
    }
    (tmp_path / "run.json").write_text(json.dumps(run))
    return tmp_path


def task(index, name, status="completed", value=None, phrase=None):
    return {"index": index, "task": name, "phrase": phrase,
            "prompt": name + (phrase or ""), "status": status, "parsed": value,
            "error": None if status == "completed" else "boom"}  # fmt: skip


def test_render_writes_detections_and_annotated_images(tmp_path):
    run_dir = write_run(
        tmp_path,
        [
            task(0, OD, value=parsed(OD, [[10, 10, 40, 50]], ["cell"])),
            task(1, GROUNDING, value=parsed(GROUNDING, [], []), phrase="platelets"),
            task(2, OD, value=parsed(OD, [[10, 10, 90, 50]], ["cell"])),
            task(3, OD, status="error"),
        ],
    )
    before = (run_dir / "run.json").read_bytes()

    summary = render(run_dir)

    statuses = [t["status"] for t in summary["tasks"]]
    assert statuses == ["detections", "no_detections", "invalid_output", "error"]
    first = summary["tasks"][0]
    assert (run_dir / first["annotated_image"]).is_file()
    saved = json.loads((run_dir / first["detections_file"]).read_text())
    assert saved == [{"cls": "cell", "conf": None, "box": [10.0, 10.0, 40.0, 50.0]}]
    assert summary["tasks"][1]["class_source"] == "prompt"
    assert (run_dir / "run.json").read_bytes() == before
    assert json.loads((run_dir / "summary.json").read_text()) == summary


def test_render_rejects_a_different_image(tmp_path):
    run_dir = write_run(tmp_path, [])
    cv2.imwrite(str(tmp_path / "img.png"), np.full((60, 80, 3), 255, np.uint8))

    with pytest.raises(ValueError, match="SHA-256"):
        render(run_dir)
