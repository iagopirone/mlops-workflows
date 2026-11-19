"""Test drawing human annotations with synthetic files."""

import json

import cv2
import numpy as np

from experiments.e2e.draw_ground_truth import draw


def test_draws_annotations_with_gt_prefix(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    assert cv2.imwrite(str(images / "a.jpg"), np.zeros((60, 80, 3), dtype=np.uint8))
    annotations = tmp_path / "annotations.json"
    annotations.write_text(json.dumps({"images": [{"image_id": "a", "width": 80, "height": 60,
                                                   "objects": [{"cls": "WBC", "box": [10, 10, 40, 50]}]}]}))  # fmt: skip

    drawn = draw(annotations, images, tmp_path / "out")

    assert drawn == [tmp_path / "out/a-ground-truth.png"]
    assert drawn[0].is_file()
    saved = json.loads((tmp_path / "out/a-ground-truth.json").read_text())
    assert saved == [{"cls": "GT:WBC", "conf": None, "box": [10.0, 10.0, 40.0, 50.0]}]
