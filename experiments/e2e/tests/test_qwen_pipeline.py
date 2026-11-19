"""Test the Qwen3-VL driver and report section with synthetic run folders only."""

import json
from datetime import UTC, datetime, timedelta

import cv2
import numpy as np
import pytest

from experiments.e2e.build_report import Manifest, build_report
from experiments.e2e.pipelines import QwenExpectations, file_sha256, run_qwen_pipeline
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.artifacts.image.image_reference import ImageReference

W, H = 80, 60
SELECTED_AT = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
HASHES = {"model.gguf": "a" * 64, "mmproj.gguf": "b" * 64}
GENERATION = ["--temp", "0.7", "--seed", "42"]
EXPECTED = QwenExpectations(
    files_sha256=HASHES,
    llama_cpp_commit="6f1e654",
    config="official_sampling",
    generation=tuple(GENERATION),
    min_process_rss_mib=2000,
)
MAPPING = {"red blood cell": "RBC", "white blood cell": "WBC", "platelet": "Platelets"}
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


def boxes(*items):
    return json.dumps([{"bbox_2d": b, "label": label} for b, label in items])


def write_image(path):
    assert cv2.imwrite(str(path), np.zeros((H, W, 3), dtype=np.uint8))
    return path


def write_run(
    run_dir, image_path, answers, started=SELECTED_AT + timedelta(hours=1), **changes
):
    """Write a run folder in the run_qwen.py format (answers: prompt -> text)."""
    run_dir.mkdir(parents=True)
    prompts = []
    for name, text in answers.items():
        (run_dir / f"{name}.stdout.txt").write_text(text, encoding="utf-8")
        (run_dir / f"{name}.stderr.txt").write_text(
            "I mtmd batch encoding done in 4400 ms\n", encoding="utf-8"
        )
        prompts.append({"name": name, "returncode": 0, "wall_seconds": 10.0,
                        "stdout_file": f"{name}.stdout.txt",
                        "stderr_file": f"{name}.stderr.txt",
                        "process_peak_mib": {"VmHWM": 3260.0, "VmSwap": 0.0}})  # fmt: skip
    run = {
        "started_at": started.isoformat(),
        "config": "official_sampling",
        "generation": GENERATION,
        "runtime": {"llama_cpp_commit": "6f1e654"},
        "model": {"files_sha256": HASHES},
        "image": {"sha256": file_sha256(image_path)},
        "memory_limit": {"memory.max": "3758096384", "memory.swap.max": "0",
                         "oom_events": "low 0\noom 0\noom_kill 0"},
        "prompts": prompts,
    }  # fmt: skip
    run |= changes
    (run_dir / "run.json").write_text(json.dumps(run), encoding="utf-8")
    return run_dir


def pipeline(run_dir, image_path, out, prompt="ground_all"):
    return run_qwen_pipeline(
        run_dir, prompt, ImageReference(name="i", location=str(image_path)), "img",
        "joint_detection", "qwen3vl", "model", out, EXPECTED,
    )  # fmt: skip


@pytest.fixture
def image(tmp_path):
    return write_image(tmp_path / "img.jpg")


def test_valid_answer_keeps_original_labels(tmp_path, image):
    # 0-1000 per axis: [125, 166, 500, 833] -> [10, 10, 40, 50] px on 80x60.
    run_dir = write_run(tmp_path / "run", image,
                        {"ground_all": boxes(([125, 166.67, 500, 833.33], "white blood cell"))})  # fmt: skip

    result = pipeline(run_dir, image, tmp_path / "out")

    assert result.status == "succeeded"
    assert all(c.passed for c in result.inference_checks)
    saved = DetectionReference(name="d", location=str(tmp_path / "out/detections.json"))
    detection = saved.materialize().data[0]
    assert detection.cls == "white blood cell"
    assert detection.conf is None
    assert detection.box == pytest.approx([10, 10, 40, 50], abs=0.01)


def test_text_answer_is_an_invalid_response_with_zero_detections(tmp_path, image):
    run_dir = write_run(tmp_path / "run", image, {"ground_platelet": "There are none."})

    result = pipeline(run_dir, image, tmp_path / "out", prompt="ground_platelet")

    assert result.status == "invalid_response"
    assert "zero usable detections" in result.error
    assert result.outputs == []


@pytest.mark.parametrize(
    ("changes", "check"),
    [
        ({"config": "original"}, "configuration"),
        ({"generation": ["--temp", "0"]}, "configuration"),
        ({"model": {"files_sha256": {"model.gguf": "c" * 64}}}, "weights"),
        ({"runtime": {"llama_cpp_commit": "other"}}, "runtime"),
        ({"image": {"sha256": "0" * 64}}, "image"),
        (
            {
                "memory_limit": {
                    "memory.max": "max",
                    "memory.swap.max": "0",
                    "oom_events": "oom_kill 0",
                }
            },
            "memory_cap",
        ),
        (
            {
                "memory_limit": {
                    "memory.max": "1",
                    "memory.swap.max": "0",
                    "oom_events": "oom_kill 1",
                }
            },
            "memory_cap",
        ),
    ],
)
def test_missing_evidence_is_an_infrastructure_failure(tmp_path, image, changes, check):
    run_dir = write_run(tmp_path / "run", image, {"ground_all": "[]"}, **changes)

    result = pipeline(run_dir, image, tmp_path / "out")

    assert result.status == "infrastructure_failure"
    assert check in result.error


def test_low_memory_means_weights_not_loaded(tmp_path, image):
    run_dir = write_run(tmp_path / "run", image, {"ground_all": "[]"})
    run = json.loads((run_dir / "run.json").read_text())
    run["prompts"][0]["process_peak_mib"]["VmHWM"] = 150.0
    (run_dir / "run.json").write_text(json.dumps(run))

    assert "weights_loaded" in pipeline(run_dir, image, tmp_path / "out").error


def test_image_not_encoded_is_an_infrastructure_failure(tmp_path, image):
    run_dir = write_run(tmp_path / "run", image, {"ground_all": "[]"})
    (run_dir / "ground_all.stderr.txt").write_text("crashed before the image")

    assert "image_encoded" in pipeline(run_dir, image, tmp_path / "out").error


def test_prompt_that_did_not_run(tmp_path, image):
    run_dir = write_run(tmp_path / "run", image, {"ground_wbc": "[]"})

    result = pipeline(run_dir, image, tmp_path / "out")

    assert result.status == "infrastructure_failure"
    assert "did not run" in result.error


@pytest.fixture
def report_setup(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    image = write_image(images / "img_a.jpg")
    gt = {"images": [{"image_id": "img_a", "width": W, "height": H, "objects": [
        {"cls": "WBC", "box": [10, 10, 40, 50]},
        {"cls": "RBC", "box": [50, 0, 70, 20]},
        {"cls": "Platelets", "box": [72, 50, 78, 58]}]}]}  # fmt: skip
    (tmp_path / "annotations.json").write_text(json.dumps(gt))
    (tmp_path / "selection.json").write_text(json.dumps({
        "created_at": SELECTED_AT.isoformat(),
        "images": [{"image_id": "img_a", "image": str(image),
                    "image_sha256": file_sha256(image)}]}))  # fmt: skip
    wbc_box = [125, 166.67, 500, 833.33]  # the WBC
    rbc_box = [625, 0, 875, 333.33]  # the RBC
    write_run(tmp_path / "runs/img_a", image, {
        # A: WBC found and named; RBC found but named "WBC"; one unknown label.
        "ground_all": boxes((wbc_box, "white blood cell"), (rbc_box, "white blood cell"),
                            ([0, 900, 50, 990], "Blood Cell")),
        "ground_rbc": boxes((rbc_box, "red blood cell")),
        "ground_wbc": boxes((wbc_box, "white blood cell")),
        "ground_platelet": "There are none.",
    })  # fmt: skip
    manifest = {
        "run_id": "qwen-test", "output_dir": str(tmp_path / "out"),
        "annotations": str(tmp_path / "annotations.json"),
        "selection": str(tmp_path / "selection.json"), "images_dir": str(images),
        "criteria": CRITERIA,
        "qwen3vl": {"model_name": "Qwen3-VL-2B Q4_K_M", "revision": "52d6c8f",
                    "files_sha256": HASHES, "llama_cpp_release": "b12119",
                    "llama_cpp_commit": "6f1e654", "config": "official_sampling",
                    "generation": GENERATION, "min_process_rss_mib": 2000,
                    "runs_dir": str(tmp_path / "runs"), "label_mapping": MAPPING},
    }  # fmt: skip
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return tmp_path, path


def build(path):
    manifest = Manifest.model_validate_json(path.read_text())
    return build_report(manifest, path, {"python": "test"}).materialize().data


def view(report, experiment, class_aware=True, subset="all_images"):
    return next(
        e for e in report.evaluations
        if e.experiment == experiment and e.class_aware == class_aware and e.subset == subset
    )  # fmt: skip


def test_joint_detection_separates_localization_and_classification(report_setup):
    _, path = report_setup
    report = build(path)

    aware = view(report, "joint_detection")
    agnostic = view(report, "joint_detection", class_aware=False)
    assert aware.class_source == "model"
    assert aware.summary["true_positives"] == 1  # only the WBC has the right label
    assert agnostic.summary["true_positives"] == 2  # WBC and RBC were both found
    assert agnostic.confusion == {"RBC": {"WBC": 1}, "WBC": {"WBC": 1}}
    assert aware.summary["out_of_vocabulary_predictions"] == 1  # "Blood Cell" kept


def test_class_conditioned_runs_are_evaluated_per_class(report_setup):
    _, path = report_setup
    report = build(path)

    rbc = view(report, "class_conditioned:RBC")
    platelets = view(report, "class_conditioned:Platelets")
    assert rbc.class_source == "prompt"
    assert set(rbc.per_class) == {"RBC"}
    assert rbc.summary["true_positives"] == 1
    assert platelets.summary["completed_inferences_with_invalid_output"] == 1
    assert platelets.summary["false_negatives"] == 1
    assert view(report, "class_conditioned:Platelets", subset="valid_responses")


def test_report_records_the_qwen_identity_and_mapping(report_setup):
    tmp_path, path = report_setup
    report = build(path)

    model = next(m for m in report.models if m.key == "qwen3vl")
    assert model.kind == "llamacpp_gguf"
    assert model.details["config"] == "official_sampling"
    evaluation = json.loads(
        (
            tmp_path
            / "out/evaluations/qwen3vl-joint_detection-class-aware-all_images.json"
        ).read_text()
    )
    assert evaluation["label_mapping"] == MAPPING
    assert evaluation["class_aware"] is True


def test_qwen_run_before_selection_aborts(report_setup):
    tmp_path, path = report_setup
    run_file = tmp_path / "runs/img_a/run.json"
    run = json.loads(run_file.read_text())
    run["started_at"] = (SELECTED_AT - timedelta(minutes=5)).isoformat()
    run_file.write_text(json.dumps(run))

    with pytest.raises(ValueError, match="before the image selection"):
        build(path)


def test_infrastructure_failures_are_left_out_only_of_completed_inferences(
    report_setup,
):
    tmp_path, path = report_setup
    run_file = tmp_path / "runs/img_a/run.json"
    run = json.loads(run_file.read_text())
    run["prompts"] = [p for p in run["prompts"] if p["name"] != "ground_wbc"]
    run_file.write_text(json.dumps(run))
    report = build(path)

    wbc = {e.subset: e.summary for e in report.evaluations
           if e.experiment == "class_conditioned:WBC" and e.class_aware}  # fmt: skip
    assert wbc["all_images"]["infrastructure_failures"] == 1
    assert wbc["all_images"]["false_negatives"] == 1  # end to end, still counted
    assert wbc["completed_inferences"]["images"] == 0  # infrastructure excluded
    platelets = {e.subset: e.summary for e in report.evaluations
                 if e.experiment == "class_conditioned:Platelets" and e.class_aware}  # fmt: skip
    # The invalid "There are none." answer stays a model failure (FN) here.
    assert "completed_inferences" not in platelets
    assert platelets["all_images"]["false_negatives"] == 1
    assert platelets["valid_responses"]["images"] == 0
