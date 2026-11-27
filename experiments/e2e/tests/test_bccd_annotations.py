"""Test the BCCD VOC conversion with synthetic files (no dataset download)."""

import json

import cv2
import numpy as np
import pytest

from experiments.e2e import bccd_annotations as bccd
from experiments.mirage.evaluate_detections import load_ground_truth


def voc_xml(width, height, objects, filename="x.jpg"):
    items = "".join(
        f"<object><name>{cls}</name><difficult>0</difficult><bndbox>"
        f"<xmin>{b[0]}</xmin><ymin>{b[1]}</ymin><xmax>{b[2]}</xmax><ymax>{b[3]}</ymax>"
        "</bndbox></object>"
        for cls, b in objects
    )
    return (
        f"<annotation><filename>{filename}</filename><size><width>{width}</width>"
        f"<height>{height}</height><depth>3</depth></size>{items}</annotation>"
    )


@pytest.fixture
def voc_root(tmp_path):
    root = tmp_path / "BCCD"
    for folder in ("Annotations", "JPEGImages", "ImageSets/Main"):
        (root / folder).mkdir(parents=True)
    return root


def add_image(root, image_id, width=64, height=48, objects=(), xml_size=None):
    image = np.zeros((height, width, 3), dtype=np.uint8)
    assert cv2.imwrite(str(root / "JPEGImages" / f"{image_id}.jpg"), image)
    w, h = xml_size or (width, height)
    (root / "Annotations" / f"{image_id}.xml").write_text(
        voc_xml(w, h, objects, f"{image_id}.jpg"), encoding="utf-8"
    )


GOOD = [("WBC", (10, 10, 30, 30))]


def test_list_image_ids_is_sorted_and_unique(tmp_path):
    split = tmp_path / "test.txt"
    split.write_text("img_3\nimg_1\n\nimg_2\nimg_1\n", encoding="utf-8")

    assert bccd.list_image_ids(split) == ["img_1", "img_2", "img_3"]


def test_one_based_pixels_become_continuous_boxes(voc_root):
    add_image(voc_root, "a", objects=[("WBC", (1, 1, 64, 48))])

    voc = bccd.read_voc(voc_root / "Annotations" / "a.xml", "one")

    assert voc["objects"] == [{"cls": "WBC", "box": [0.0, 0.0, 64.0, 48.0]}]


def test_zero_based_pixels_are_kept(voc_root):
    add_image(voc_root, "a", objects=[("RBC", (5, 6, 20, 30))])

    voc = bccd.read_voc(voc_root / "Annotations" / "a.xml", "zero")

    assert voc["objects"][0]["box"] == [5.0, 6.0, 20.0, 30.0]


@pytest.mark.parametrize(
    ("objects", "xml_size", "reason"),
    [
        ([("Neutrophil", (1, 1, 5, 5))], None, "unknown class"),
        ([("RBC", (1, 1, 65, 10))], None, "invalid annotation"),
        (GOOD, (640, 480), "differs from the image"),
        ([("RBC", (1, 1, 10, 10)), ("RBC", (1, 1, 10, 10))], None, "duplicate"),
        ([("RBC", (1, 1, 21, 21)), ("RBC", (1, 1, 21, 20.5))], None, "duplicate"),
    ],
)
def test_ineligible_images(voc_root, objects, xml_size, reason):
    add_image(voc_root, "a", objects=objects, xml_size=xml_size)

    with pytest.raises(bccd.IneligibleImageError, match=reason):
        bccd.inspect_image(voc_root, "a", "one")


def test_overlapping_cells_below_threshold_are_not_duplicates():
    objects = [
        {"cls": "RBC", "box": [0, 0, 10, 10]},
        {"cls": "RBC", "box": [2, 0, 12, 10]},  # IoU 0.667
        {"cls": "WBC", "box": [0, 0, 10, 10]},  # other class
    ]

    assert bccd.find_duplicates(objects) == []


def test_missing_files_are_ineligible(voc_root):
    with pytest.raises(bccd.IneligibleImageError, match="missing XML or JPEG"):
        bccd.inspect_image(voc_root, "absent", "one")


def test_ineligible_images_are_replaced_by_the_next_candidates(voc_root):
    add_image(voc_root, "a", objects=GOOD)
    add_image(voc_root, "b", objects=[("RBC", (1, 1, 9, 9)), ("RBC", (1, 1, 9, 9))])
    add_image(voc_root, "c", objects=GOOD)
    add_image(voc_root, "d", objects=[("Neutrophil", (1, 1, 5, 5))])
    add_image(voc_root, "e", objects=GOOD)
    add_image(voc_root, "f", objects=GOOD)

    annotations, selection = bccd.select_images(
        voc_root, ["a", "b", "c", "d", "e", "f"], 3, "one", {"c": "seed image"}
    )

    assert [image["image_id"] for image in annotations["images"]] == ["a", "e", "f"]
    assert [(x["image_id"], x["reason"][:9]) for x in selection["excluded"]] == [
        ("b", "suspiciou"),
        ("c", "seed imag"),
        ("d", "unreadabl"),
    ]
    assert selection["substitutions"] == [
        {"excluded": "b", "replaced_by": "e"},
        {"excluded": "c", "replaced_by": "f"},
    ]
    assert selection["candidate_ids"] == ["a", "b", "c", "d", "e", "f"]
    assert all(len(x["xml_sha256"]) == 64 for x in selection["excluded"])


def test_dataset_files_are_never_modified(voc_root):
    add_image(voc_root, "a", objects=[("RBC", (1, 1, 9, 9)), ("RBC", (1, 1, 9, 9))])
    add_image(voc_root, "b", objects=GOOD)
    files = sorted(voc_root.rglob("*.*"))
    before = {path: path.read_bytes() for path in files}

    bccd.select_images(voc_root, ["a", "b"], 1, "one")

    assert {path: path.read_bytes() for path in files} == before


def test_not_enough_eligible_images(voc_root):
    add_image(voc_root, "a", objects=GOOD)

    with pytest.raises(ValueError, match="Only 1 eligible"):
        bccd.select_images(voc_root, ["a", "b"], 2, "one")


def run_main(voc_root, out, *extra):
    return bccd.main(
        ["--voc-root", str(voc_root), "--image-list", "test.txt", "--limit", "2",
         "--pixel-origin", "one", "--output-dir", str(out), *extra]
    )  # fmt: skip


def test_main_output_is_accepted_by_the_evaluator(voc_root, tmp_path):
    add_image(voc_root, "b", objects=[("Platelets", (3, 4, 9, 12))])
    add_image(voc_root, "a", objects=[])
    add_image(voc_root, "c", objects=GOOD)
    (voc_root / "ImageSets" / "Main" / "test.txt").write_text("c\nb\na\n")
    seeds = tmp_path / "seeds.txt"
    seeds.write_text("a\n")
    out = tmp_path / "out"

    code = run_main(
        voc_root, out, "--exclude-ids", str(seeds), "--exclude-reason", "seed"
    )

    assert code == 0
    ground_truth = load_ground_truth(out / "annotations.json")
    assert sorted(ground_truth) == ["b", "c"]
    assert ground_truth["b"]["objects"] == [
        {"cls": "Platelets", "box": [2.0, 3.0, 9.0, 12.0]}
    ]
    selection = json.loads((out / "selection.json").read_text())
    assert selection["excluded"][0]["image_id"] == "a"
    assert selection["exclude_ids_sha256"]
    assert selection["created_at"].endswith("+00:00")


def test_main_requires_reason_with_exclusion_list(voc_root, tmp_path):
    with pytest.raises(SystemExit):
        run_main(voc_root, tmp_path / "out", "--exclude-ids", str(tmp_path / "x"))


def test_main_reports_errors_without_writing(voc_root, tmp_path, capsys):
    (voc_root / "ImageSets" / "Main" / "test.txt").write_text("a\n")
    out = tmp_path / "out"

    assert run_main(voc_root, out) == 1
    assert "cannot select 2" in capsys.readouterr().err
    assert not out.exists()


@pytest.mark.parametrize(
    ("classes", "ok"),
    [(["RBC", "WBC", "Platelets"], True), (("Platelets", "RBC", "WBC"), True),
     (["RBC", "WBC"], False), (["rbc", "wbc", "platelets"], False)],
)  # fmt: skip
def test_check_class_names(classes, ok):
    if ok:
        bccd.check_class_names(classes)
    else:
        with pytest.raises(ValueError, match="differ"):
            bccd.check_class_names(classes)
