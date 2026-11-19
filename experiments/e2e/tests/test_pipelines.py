"""Test the pipeline drivers with simulated inputs only.

The YOLO driver uses a FakeDetector (plus an optional real-ONNX test that needs
an explicit opt-in). The MIRAGE driver reads run folders written by the test in
the run_poc.py format; no model is loaded or simulated inside the driver.
"""

import json
import os
from pathlib import Path

import cv2
import numpy as np
import pytest

from experiments.e2e.pipelines import (
    MirageExpectations,
    file_sha256,
    run_mirage_pipeline,
    run_yolo_pipeline,
)
from experiments.e2e.training_format import training_answer_to_json
from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.artifacts.report.execution_report import InferenceCheck
from mlops_workflows.components.object_detection.detectors.yolo_detector import (
    YoloDetector,
    YoloDetectorConfig,
)
from mlops_workflows.components.object_detection.object_detector import ObjectDetector

WIDTH, HEIGHT = 80, 60
# Real models run only with this extra, explicit opt-in, even when model paths
# are configured for the main suite.
REAL_MODELS_FLAG = "E2E_ALLOW_REAL_MODELS"
PROMPT = "Return JSON."
EXPECTED = MirageExpectations(
    official_revision="617751c", checkpoint_name="mirage-ckpt", min_gpu_memory_mib=16000
)
CHECKS = [InferenceCheck(name="test", passed=True, detail="synthetic")]


class FakeDetector(ObjectDetector):
    """Return predefined detections without running a model."""

    def detect(self, image: np.ndarray) -> list[Detection]:
        return [Detection(cls="WBC", conf=0.9, box=[10.0, 10.0, 40.0, 40.0])]


class BrokenDetector(ObjectDetector):
    """Fail like a model that cannot run."""

    def detect(self, image: np.ndarray) -> list[Detection]:
        raise RuntimeError("ONNX session failed")


@pytest.fixture
def image(tmp_path) -> ImageReference:
    path = tmp_path / "img.png"
    assert cv2.imwrite(str(path), np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8))
    return ImageReference(name="img", location=str(path))


def make_run(tmp_path, answer=None, stdout=True, size=(WIDTH, HEIGHT), **changes):
    """Write a run folder in the run_poc.py format, as a real run would."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run = {
        "images": [
            {"path": "/gpu/images/img.png", "width": size[0], "height": size[1]}
        ],
        "answer_image": "/gpu/images/img.png",
        "returncode": 0,
        "duration_seconds": 12.5,
        "prompt": PROMPT,
        "official_repo": {"path": "/gpu/mirage", "revision": "617751c", "dirty": False},
        "parameters": {
            "model_path_resolved": "/gpu/ckpt/mirage-ckpt",
            "allow_remote_model": False,
        },
        "environment": {
            "gpu": "NVIDIA L4, 23034 MiB",
            "hf_hub_offline": "1",
            "gpu_memory_peak_mib": 20100,
        },
    }
    for key, value in changes.items():
        section, _, field = key.partition("__")
        if field:
            run[section][field] = value
        else:
            run[section] = value
    (run_dir / "run.json").write_text(json.dumps(run), encoding="utf-8")
    (run_dir / "stderr.txt").write_text("", encoding="utf-8")
    if stdout:
        (run_dir / "stdout.txt").write_text(
            f"---Output---\nText Output: {answer}\n", encoding="utf-8"
        )
    if answer is not None:
        (run_dir / "answer.txt").write_text(answer, encoding="utf-8")
    return run_dir


def mirage(run_dir, image, out, convert=None):
    return run_mirage_pipeline(
        run_dir, image, "img", "json_prompt", "mirage", "normalized_padded_square",
        out, PROMPT, EXPECTED, convert,
    )  # fmt: skip


def test_yolo_pipeline_writes_detections_and_annotated_image(tmp_path, image):
    result = run_yolo_pipeline(
        image, "img", FakeDetector(), "yolo", tmp_path / "out", CHECKS
    )

    assert result.status == "succeeded"
    assert result.class_source == "model"
    assert result.detection_count == 1
    locations = {item.kind: item for item in result.outputs}
    assert locations["image"].sha256 == file_sha256(Path(locations["image"].location))
    assert DetectionReference(name="d", location=locations["detection"].location)


def test_yolo_pipeline_records_infrastructure_failure(tmp_path, image):
    result = run_yolo_pipeline(
        image, "img", BrokenDetector(), "yolo", tmp_path / "out", CHECKS
    )

    assert result.status == "infrastructure_failure"
    assert "ONNX session failed" in result.error
    assert result.outputs == []


def test_yolo_pipeline_with_real_model(tmp_path):
    model_path = os.environ.get("DETECTION_MODEL_PATH")
    image_path = os.environ.get("DETECTION_IMAGE_PATH")
    if not model_path or not image_path:
        pytest.skip("Detection model and image paths are not configured.")
    if os.environ.get(REAL_MODELS_FLAG) != "1":
        pytest.skip(
            f"Real inference needs explicit approval: set {REAL_MODELS_FLAG}=1."
        )
    detector = YoloDetector(YoloDetectorConfig(model_path=model_path))

    result = run_yolo_pipeline(
        ImageReference(name="real", location=image_path),
        "real", detector, "yolo", tmp_path, CHECKS,
    )  # fmt: skip

    assert result.status == "succeeded"
    assert result.detection_count > 0


def test_mirage_valid_answer_goes_through_existing_components(tmp_path, image):
    # 80x60 image -> square side 80, vertical padding 10.
    answer = '[{"cls": "WBC", "box": [0.125, 0.25, 0.5, 0.75]}]'
    run_dir = make_run(tmp_path, answer=answer)

    result = mirage(run_dir, image, tmp_path / "out")

    assert result.status == "succeeded"
    assert result.class_source == "model"
    assert result.detection_count == 1
    assert result.duration_seconds == 12.5
    assert all(check.passed for check in result.inference_checks)
    detection_file = next(r.location for r in result.outputs if r.kind == "detection")
    saved = DetectionReference(name="d", location=detection_file).materialize().data
    assert saved[0].conf is None
    assert saved[0].box == [10.0, 10.0, 40.0, 50.0]
    answer_record = next(r for r in result.inputs if r.kind == "text")
    assert answer_record.location.endswith("answer.txt")
    assert answer_record.sha256 == file_sha256(run_dir / "answer.txt")
    assert {Path(r.location).name for r in result.evidence} == {
        "run.json",
        "stdout.txt",
        "stderr.txt",
    }


def test_mirage_empty_list_is_a_valid_answer(tmp_path, image):
    result = mirage(make_run(tmp_path, answer="[]"), image, tmp_path / "out")

    assert result.status == "succeeded"
    assert result.detection_count == 0


@pytest.mark.parametrize(
    "answer",
    ["I see red blood cells.", "[0.1, 0.2, 0.3, 0.4]", '[{"cls": "WBC", "box": [0.1, 0.2, 0.3, 0.4], "conf": 0.9}]'],
)  # fmt: skip
def test_mirage_invalid_answer_is_not_converted(tmp_path, image, answer):
    out = tmp_path / "out"
    run_dir = make_run(tmp_path, answer=answer)

    result = mirage(run_dir, image, out)

    assert result.status == "invalid_response"
    assert result.error
    assert result.outputs == []
    assert not (out / "detections.json").exists()
    assert (run_dir / "answer.txt").read_text(encoding="utf-8") == answer


def test_training_format_answer_uses_the_prompt_class(tmp_path, image):
    out = tmp_path / "out"
    run_dir = make_run(tmp_path, answer="[0.125, 0.25, 0.5, 0.75]")

    result = mirage(
        run_dir, image, out, lambda text: training_answer_to_json(text, "WBC")
    )

    assert result.status == "succeeded"
    assert result.class_source == "prompt"
    converted = next(r for r in result.outputs if r.kind == "text")
    assert Path(converted.location).name == "answer-converted.json"
    saved = DetectionReference(name="d", location=str(out / "detections.json"))
    assert saved.materialize().data[0].cls == "WBC"
    assert (run_dir / "answer.txt").read_text() == "[0.125, 0.25, 0.5, 0.75]"


def test_training_format_mismatch_is_an_invalid_response(tmp_path, image):
    run_dir = make_run(tmp_path, answer="The WBC is in the center.")

    result = mirage(
        run_dir,
        image,
        tmp_path / "out",
        lambda text: training_answer_to_json(text, "WBC"),
    )

    assert result.status == "invalid_response"
    assert result.error.startswith("format_mismatch")
    assert result.class_source == "prompt"


@pytest.mark.parametrize(
    ("changes", "check"),
    [
        ({"official_repo__revision": "other"}, "official_code_revision"),
        ({"official_repo__dirty": True}, "official_code_revision"),
        ({"parameters__model_path_resolved": "/gpu/x/model"}, "checkpoint"),
        ({"parameters__allow_remote_model": True}, "checkpoint"),
        ({"prompt": "another prompt"}, "prompt"),
        ({"environment__hf_hub_offline": None}, "offline"),
        ({"environment__gpu": None}, "gpu_present"),
        ({"environment__gpu_memory_peak_mib": 900}, "gpu_memory_loaded"),
        ({"environment__gpu_memory_peak_mib": None}, "gpu_memory_loaded"),
    ],
)
def test_missing_evidence_of_real_inference_is_an_infrastructure_failure(
    tmp_path, image, changes, check
):
    result = mirage(make_run(tmp_path, answer="[]", **changes), image, tmp_path / "o")

    assert result.status == "infrastructure_failure"
    assert check in result.error
    assert not next(c for c in result.inference_checks if c.name == check).passed


def test_stdout_without_official_markers_is_an_infrastructure_failure(tmp_path, image):
    run_dir = make_run(tmp_path, answer="[]")
    (run_dir / "stdout.txt").write_text("something else", encoding="utf-8")

    result = mirage(run_dir, image, tmp_path / "out")

    assert result.status == "infrastructure_failure"
    assert "official_output_markers" in result.error


def test_mirage_failed_process_is_infrastructure_failure(tmp_path, image):
    result = mirage(make_run(tmp_path, returncode=1), image, tmp_path / "out")

    assert result.status == "infrastructure_failure"
    assert "exited with code 1" in result.error


def test_mirage_without_answer_marker_is_infrastructure_failure(tmp_path, image):
    result = mirage(make_run(tmp_path), image, tmp_path / "out")

    assert result.status == "infrastructure_failure"
    assert "Text Output" in result.error


def test_mirage_without_stdout_is_infrastructure_failure(tmp_path, image):
    result = mirage(
        make_run(tmp_path, answer="[]", stdout=False), image, tmp_path / "o"
    )

    assert result.status == "infrastructure_failure"


def test_mirage_without_run_json_is_infrastructure_failure(tmp_path, image):
    run_dir = tmp_path / "empty"
    run_dir.mkdir()

    result = mirage(run_dir, image, tmp_path / "out")

    assert result.status == "infrastructure_failure"
    assert result.duration_seconds is None


def test_mirage_run_of_another_image_aborts(tmp_path, image):
    run_dir = make_run(tmp_path, answer="[]", size=(640, 480))

    with pytest.raises(ValueError, match="differs"):
        mirage(run_dir, image, tmp_path / "out")


def test_mirage_run_with_several_images_aborts(tmp_path, image):
    run_dir = make_run(tmp_path, answer="[]", answer_image=None)

    with pytest.raises(ValueError, match="one image"):
        mirage(run_dir, image, tmp_path / "out")
