"""Test the report tool end to end with synthetic files only.

The YOLO part uses a FakeDetector with synthetic checks (allowed only in tests);
the MIRAGE runs are folders written by the test in the run_poc.py format.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
import pytest

from experiments.e2e.build_report import (
    Manifest,
    build_report,
    verify_report,
    yolo_inference_checks,
)
from experiments.e2e.pipelines import file_sha256
from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.artifacts.report.execution_report import InferenceCheck
from mlops_workflows.components.object_detection.object_detector import ObjectDetector

W, H = 80, 60
SELECTED_AT = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
CRITERIA = {
    "iou_threshold": 0.5,
    "positive_min_valid_response_rate": 0.8,
    "positive_min_precision": 0.5,
    "positive_min_recall": 0.5,
    "positive_min_mean_matched_iou": 0.6,
    "positive_max_false_positives_per_image": 1.0,
    "negative_max_valid_response_rate": 0.5,
    "negative_max_precision": 0.2,
}
JSON_PROMPT = "Return JSON."
WBC_PROMPT = "Please provide the bounding box coordinate of the region this sentence describes: a white blood cell."
# 80x60 image: square side 80, vertical padding 10. Pixel box [10, 10, 40, 50].
NORMALIZED = [0.125, 0.25, 0.5, 0.75]


class FakeDetector(ObjectDetector):
    def detect(self, image):
        return [
            Detection(cls="WBC", conf=0.9, box=[10.0, 10.0, 40.0, 50.0]),
            Detection(cls="RBC", conf=0.5, box=[60.0, 0.0, 70.0, 10.0]),
        ]


SYNTHETIC_CHECKS = [InferenceCheck(name="synthetic", passed=True, detail="test only")]


def write_run(
    run_dir, image_name, answer, prompt, started=SELECTED_AT + timedelta(hours=1)
):
    run_dir.mkdir(parents=True)
    run = {
        "started_at_utc": started.isoformat(),
        "images": [{"path": f"/gpu/{image_name}", "width": W, "height": H}],
        "answer_image": f"/gpu/{image_name}",
        "returncode": 0,
        "duration_seconds": 30.0,
        "prompt": prompt,
        "official_repo": {"revision": "617751c", "dirty": False},
        "parameters": {"model_path_resolved": "/gpu/mirage-ckpt", "allow_remote_model": False},
        "environment": {"gpu": "NVIDIA L4", "hf_hub_offline": "1", "gpu_memory_peak_mib": 20000},
    }  # fmt: skip
    (run_dir / "run.json").write_text(json.dumps(run))
    (run_dir / "stdout.txt").write_text(f"---Output---\nText Output: {answer}\n")
    (run_dir / "stderr.txt").write_text("")
    (run_dir / "answer.txt").write_text(answer)


@pytest.fixture
def setup(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    records, gt = [], []
    for image_id in ("img_a", "img_b"):
        path = images / f"{image_id}.jpg"
        assert cv2.imwrite(str(path), np.zeros((H, W, 3), dtype=np.uint8))
        records.append(
            {
                "image_id": image_id,
                "image": str(path),
                "image_sha256": file_sha256(path),
            }
        )
        gt.append({"image_id": image_id, "width": W, "height": H,
                   "objects": [{"cls": "WBC", "box": [10, 10, 40, 50]},
                               {"cls": "RBC", "box": [0, 0, 8, 8]}]})  # fmt: skip
    (tmp_path / "annotations.json").write_text(json.dumps({"images": gt}))
    (tmp_path / "selection.json").write_text(
        json.dumps({"created_at": SELECTED_AT.isoformat(), "images": records})
    )
    (tmp_path / "json.txt").write_text(JSON_PROMPT + "\n")
    (tmp_path / "wbc.txt").write_text(WBC_PROMPT + "\n")
    good = json.dumps([{"cls": "WBC", "box": NORMALIZED}])
    write_run(tmp_path / "runs/json/img_a", "img_a.jpg", good, JSON_PROMPT)
    write_run(tmp_path / "runs/json/img_b", "img_b.jpg", "Some cells.", JSON_PROMPT)
    write_run(tmp_path / "runs/wbc/img_a", "img_a.jpg", str(NORMALIZED), WBC_PROMPT)
    write_run(
        tmp_path / "runs/wbc/img_b", "img_b.jpg", "[0.9, 0.1, 0.95, 0.2]", WBC_PROMPT
    )
    model = tmp_path / "best.onnx"
    model.write_bytes(b"not a real model")
    manifest = {
        "run_id": "e2e-test",
        "output_dir": str(tmp_path / "out"),
        "annotations": str(tmp_path / "annotations.json"),
        "selection": str(tmp_path / "selection.json"),
        "images_dir": str(images),
        "criteria": CRITERIA,
        "yolo": {"model_path": str(model), "confidence_threshold": 0.25, "iou_threshold": 0.5},
        "mirage": {
            "model_name": "tsunghanwu/mirage-llama3.1-8.3B",
            "checkpoint_name": "mirage-ckpt",
            "checkpoint_revision": "100ea29",
            "clip_revision": "ce19dc9",
            "official_revision": "617751c",
            "min_gpu_memory_mib": 16000,
            "experiments": [
                {"name": "json_prompt", "prompt_file": str(tmp_path / "json.txt"),
                 "runs_dir": str(tmp_path / "runs/json")},
                {"name": "training_grounding:WBC", "prompt_file": str(tmp_path / "wbc.txt"),
                 "runs_dir": str(tmp_path / "runs/wbc"), "prompt_class": "WBC"},
            ],
        },
        "deviations": ["synthetic test"],
    }  # fmt: skip
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return tmp_path, path


def build(setup, **changes):
    _, path = setup
    data = json.loads(path.read_text()) | changes
    path.write_text(json.dumps(data))
    manifest = Manifest.model_validate_json(path.read_text())
    return build_report(
        manifest, path, {"python": "test"}, FakeDetector(), SYNTHETIC_CHECKS
    )


def test_report_is_saved_reloaded_and_verified(setup):
    reference = build(setup)

    report = reference.materialize().data
    assert verify_report(reference) == []
    assert [m.key for m in report.models] == ["yolo", "mirage"]
    assert report.criteria["iou_threshold"] == 0.5
    assert {(e.pipeline, e.experiment) for e in report.evaluations} == {
        ("yolo", "detection"),
        ("mirage", "json_prompt"),
        ("mirage", "training_grounding:WBC"),
    }


def test_statuses_and_class_sources(setup):
    report = build(setup).materialize().data
    runs = {(r.experiment, r.image_id): r for r in report.pipelines}

    assert runs[("detection", "img_a")].status == "succeeded"
    assert runs[("json_prompt", "img_a")].status == "succeeded"
    assert runs[("json_prompt", "img_b")].status == "invalid_response"
    assert runs[("training_grounding:WBC", "img_a")].class_source == "prompt"
    assert runs[("json_prompt", "img_a")].class_source == "model"


def test_evaluations_keep_experiments_apart(setup):
    report = build(setup).materialize().data
    evaluations = {
        e.experiment: e
        for e in report.evaluations
        if e.class_aware and e.subset == "all_images"
    }

    json_prompt = evaluations["json_prompt"].summary
    assert json_prompt["true_positives"] == 1
    assert json_prompt["false_negatives"] == 3  # img_a RBC + both of img_b
    assert json_prompt["completed_inferences_with_invalid_output"] == 1
    assert json_prompt["valid_response_rate"] == 0.5
    assert json_prompt["images_with_correct_localization"] == 1

    grounding = evaluations["training_grounding:WBC"]
    assert grounding.class_source == "prompt"
    # Only WBC annotations count; img_b's box misses the WBC.
    assert grounding.summary["true_positives"] == 1
    assert grounding.summary["false_positives"] == 1
    assert grounding.summary["false_negatives"] == 1
    assert set(grounding.per_class) == {"WBC"}

    yolo = evaluations["detection"].summary
    assert yolo["true_positives"] == 2
    assert yolo["false_positives"] == 2
    assert yolo["mean_false_positives_per_image"] == 1.0


def test_evaluator_output_is_saved_with_hash(setup):
    report = build(setup).materialize().data

    for evaluation in report.evaluations:
        path = Path(evaluation.report.location)
        assert json.loads(path.read_text())["summary"] == evaluation.summary
        assert evaluation.report.sha256 == file_sha256(path)


def test_annotated_images_are_recovered_from_the_report(setup):
    report = build(setup).materialize().data
    images = [o for r in report.pipelines for o in r.outputs if o.kind == "image"]

    assert images
    for item in images:
        assert ImageReference(name=item.name, location=item.location).materialize()


def test_missing_run_folder_is_an_infrastructure_failure(setup):
    tmp_path, _ = setup
    for name in ("run.json", "stdout.txt", "stderr.txt", "answer.txt"):
        (tmp_path / "runs/json/img_b" / name).unlink()

    report = build(setup).materialize().data
    run = next(
        r
        for r in report.pipelines
        if (r.experiment, r.image_id) == ("json_prompt", "img_b")
    )
    assert run.status == "infrastructure_failure"


def test_run_before_selection_aborts(setup):
    tmp_path, _ = setup
    run_file = tmp_path / "runs/json/img_a/run.json"
    run = json.loads(run_file.read_text())
    run["started_at_utc"] = (SELECTED_AT - timedelta(minutes=1)).isoformat()
    run_file.write_text(json.dumps(run))

    with pytest.raises(ValueError, match="before the image selection"):
        build(setup)


def test_changed_image_aborts(setup):
    tmp_path, _ = setup
    cv2.imwrite(str(tmp_path / "images/img_a.jpg"), np.full((H, W, 3), 255, np.uint8))

    with pytest.raises(ValueError, match="SHA-256"):
        build(setup)


def test_criteria_must_be_pre_registered(setup):
    with pytest.raises(ValueError, match="criteria missing"):
        build(setup, criteria={"iou_threshold": 0.5})


def test_yolo_needs_real_inference_checks(setup):
    _, path = setup
    manifest = Manifest.model_validate_json(path.read_text())

    with pytest.raises(ValueError, match="detector and its checks"):
        build_report(manifest, path, {}, FakeDetector(), [])


def test_tampered_output_is_detected(setup):
    reference = build(setup)
    report = reference.materialize().data
    annotated = next(
        o for r in report.pipelines for o in r.outputs if o.kind == "image"
    )
    Path(annotated.location).write_bytes(b"changed")

    assert verify_report(reference) == [f"hash mismatch {annotated.location}"]


def test_fake_detector_fails_the_yolo_checks(tmp_path):
    checks = yolo_inference_checks(FakeDetector(), str(tmp_path / "best.onnx"))

    assert [(c.name, c.passed) for c in checks] == [("detector_class", False)]


def test_manifest_rejects_unknown_fields(setup):
    _, path = setup
    data = json.loads(path.read_text()) | {"surprise": 1}

    with pytest.raises(ValueError):
        Manifest.model_validate_json(json.dumps(data))


def test_each_experiment_has_class_aware_agnostic_and_valid_subset(setup):
    report = build(setup).materialize().data
    kinds = {
        (e.experiment, e.class_aware, e.subset)
        for e in report.evaluations
        if e.pipeline == "mirage"
    }

    assert ("json_prompt", True, "all_images") in kinds
    assert ("json_prompt", False, "all_images") in kinds
    # img_b's JSON answer was invalid, so the valid-responses view is added too.
    assert ("json_prompt", True, "valid_responses") in kinds
    assert ("json_prompt", False, "valid_responses") in kinds


def test_valid_subset_is_reported_next_to_all_images(setup):
    report = build(setup).materialize().data
    views = {
        e.subset: e.summary
        for e in report.evaluations
        if e.experiment == "json_prompt" and e.class_aware
    }

    assert views["all_images"]["images"] == 2
    assert views["valid_responses"]["images"] == 1
    assert views["valid_responses"]["completed_inferences_with_invalid_output"] == 1


def test_yolo_class_agnostic_confusion(setup):
    report = build(setup).materialize().data
    agnostic = next(
        e for e in report.evaluations if e.pipeline == "yolo" and not e.class_aware
    )

    # FakeDetector: WBC box on the WBC annotation, RBC box far from the RBC.
    assert agnostic.confusion == {"WBC": {"WBC": 2}}
