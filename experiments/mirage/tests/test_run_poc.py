"""Offline tests; never import the MIRAGE model or execute GPU inference.

Fixtures are built with the standard library only, so these tests also run
under the Python 3.10 interpreter of the MIRAGE environment.
"""

from __future__ import annotations

import importlib.util
import json
import os
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "run_poc.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("mirage_runner", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


runner = _load_module()


def png_bytes(width: int, height: int) -> bytes:
    """Build a minimal valid grayscale PNG."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    pixels = zlib.compress(b"".join(b"\x00" + b"\x00" * width for _ in range(height)))
    return (
        runner.PNG_SIGNATURE
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", pixels)
        + chunk(b"IEND", b"")
    )


def jpeg_bytes(width: int, height: int, orientation: int | None = None) -> bytes:
    """Build JPEG headers (SOI, optional EXIF APP1, SOF0, EOI) for header tests."""
    data = b"\xff\xd8"
    if orientation is not None:
        ifd = struct.pack(">H", 1) + struct.pack(">HHIHH", 0x0112, 3, 1, orientation, 0)
        tiff = b"MM" + struct.pack(">HI", 42, 8) + ifd + struct.pack(">I", 0)
        app1 = b"Exif\x00\x00" + tiff
        data += b"\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1
    sof = struct.pack(">BHHB", 8, height, width, 1) + b"\x01\x11\x00"
    data += b"\xff\xc0" + struct.pack(">H", len(sof) + 2) + sof
    return data + b"\xff\xd9"


def bmp_bytes(width: int, height: int) -> bytes:
    """Build a BMP header (BITMAPINFOHEADER), optionally top-down."""
    info = struct.pack("<IiiHH", 40, width, height, 1, 24) + b"\x00" * 24
    return b"BM" + struct.pack("<IHHI", 14 + len(info), 0, 0, 14 + len(info)) + info


@pytest.fixture
def official_repo(tmp_path: Path) -> Path:
    """Create a stand-in for the official repository with a harmless demo.py."""
    repo = tmp_path / "official"
    repo.mkdir()
    (repo / "demo.py").write_text("", encoding="utf-8")
    return repo


def write_fake_demo(repo: Path, answer: str, retrieved_index: int = 0) -> None:
    """Write a demo.py that prints the official output format without a model."""
    (repo / "demo.py").write_text(
        "import argparse, os\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--model-path'); p.add_argument('--image-folder')\n"
        "p.add_argument('--prompt'); p.add_argument('--max-num-retrievals')\n"
        "a = p.parse_args()\n"
        "paths = [os.path.join(a.image_folder, n) for n in os.listdir(a.image_folder)]\n"
        "paths = sorted(paths, reverse=True)  # Differ from the sorted listing.\n"
        "print('---Input---')\n"
        "print('Prompt:', a.prompt)\n"
        "print('Images:', paths)\n"
        "print('---Output---')\n"
        f"print('Text Output:', {answer!r})\n"
        f"print('Retrieval Image:', [sorted(paths)[{retrieved_index}]])\n",
        encoding="utf-8",
    )


def run_script(*args: str, env=None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def base_args(repo: Path, folder: Path, prompt: Path, out: Path, model: str):
    return [
        "--official-repo",
        str(repo),
        "--image-folder",
        str(folder),
        "--prompt-file",
        str(prompt),
        "--model-path",
        model,
        "--output-dir",
        str(out),
    ]


@pytest.fixture
def prompt_file(tmp_path: Path) -> Path:
    path = tmp_path / "prompt.txt"
    path.write_text("What is in this picture?", encoding="utf-8")
    return path


def test_dry_run_does_not_execute_or_write_output(tmp_path, official_repo, prompt_file):
    # If executed, this script would write an unwanted file.
    (official_repo / "demo.py").write_text(
        "from pathlib import Path\nPath('EXECUTED').write_text('yes')\n",
        encoding="utf-8",
    )
    folder = tmp_path / "images"
    folder.mkdir()
    (folder / "test.png").write_bytes(png_bytes(64, 48))
    out = tmp_path / "results"

    result = run_script(
        *base_args(official_repo, folder, prompt_file, out, "mirage-not-downloaded")
    )

    assert result.returncode == 0, result.stderr
    assert "DRY RUN" in result.stdout
    assert "64x48" in result.stdout
    assert "Single image" in result.stdout
    assert not (official_repo / "EXECUTED").exists()
    assert not out.exists()


def test_dry_run_rejects_non_image_files(tmp_path, official_repo, prompt_file):
    folder = tmp_path / "images"
    folder.mkdir()
    (folder / "image.png").write_bytes(png_bytes(4, 4))
    (folder / "notes.txt").write_text("unexpected", encoding="utf-8")

    result = run_script(
        *base_args(official_repo, folder, prompt_file, tmp_path / "out", "mirage")
    )

    assert result.returncode != 0
    assert "only supported image files" in result.stderr


def test_dry_run_rejects_unreadable_image_header(tmp_path, official_repo, prompt_file):
    folder = tmp_path / "images"
    folder.mkdir()
    (folder / "fake.png").write_bytes(b"not really a PNG")

    result = run_script(
        *base_args(official_repo, folder, prompt_file, tmp_path / "out", "mirage")
    )

    assert result.returncode != 0
    assert "Unsupported or unreadable image header" in result.stderr


def test_dry_run_rejects_exif_rotated_jpeg(tmp_path, official_repo, prompt_file):
    folder = tmp_path / "images"
    folder.mkdir()
    (folder / "rotated.jpg").write_bytes(jpeg_bytes(640, 480, orientation=6))

    result = run_script(
        *base_args(official_repo, folder, prompt_file, tmp_path / "out", "mirage")
    )

    assert result.returncode != 0
    assert "EXIF orientation 6" in result.stderr


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (png_bytes(640, 480), {"width": 640, "height": 480, "exif_orientation": None}),
        (jpeg_bytes(640, 480), {"width": 640, "height": 480, "exif_orientation": None}),
        (
            jpeg_bytes(640, 480, orientation=1),
            {"width": 640, "height": 480, "exif_orientation": 1},
        ),
        (
            jpeg_bytes(640, 480, orientation=6),
            {"width": 640, "height": 480, "exif_orientation": 6},
        ),
        (bmp_bytes(320, 200), {"width": 320, "height": 200, "exif_orientation": None}),
        (bmp_bytes(320, -200), {"width": 320, "height": 200, "exif_orientation": None}),
    ],
)
def test_read_image_info(tmp_path, data, expected):
    path = tmp_path / "image.bin"
    path.write_bytes(data)

    assert runner.read_image_info(path) == expected


@pytest.mark.parametrize(
    "data",
    [b"", b"GIF89a....", b"\xff\xd8\xff\xd9", png_bytes(1, 1)[:12]],
)
def test_read_image_info_rejects_invalid_headers(tmp_path, data):
    path = tmp_path / "image.bin"
    path.write_bytes(data)

    with pytest.raises(ValueError):
        runner.read_image_info(path)


def test_extract_text_output():
    stdout = (
        "---Input---\nPrompt: test\n---Output---\n"
        "Text Output: First line\nsecond line\n"
        "Retrieval Image: ['/tmp/a.jpg']\n"
    )
    assert runner.extract_text_output(stdout) == "First line\nsecond line"
    assert runner.extract_text_output("unrelated output") is None


def test_extract_text_output_keeps_marker_inside_answer():
    stdout = (
        "---Output---\nText Output: The phrase Retrieval Image: appears here\n"
        "Retrieval Image: ['/tmp/a.jpg']\n"
    )
    assert (
        runner.extract_text_output(stdout) == "The phrase Retrieval Image: appears here"
    )


def test_extract_printed_lists():
    stdout = (
        "---Input---\nPrompt: Images: not this line\n"
        "Images: ['/i/b.png', '/i/a.png']\n---Output---\n"
        "Text Output: ok\nRetrieval Image: ['/i/a.png']\n"
    )
    assert runner.extract_printed_list(stdout, "Images:") == ["/i/b.png", "/i/a.png"]
    assert runner.extract_printed_list(stdout, "Retrieval Image:") == ["/i/a.png"]
    assert runner.extract_printed_list("no markers", "Images:") is None
    assert (
        runner.extract_printed_list(
            "---Output---\nRetrieval Image: oops", "Retrieval Image:"
        )
        is None
    )


def test_describe_images_matches_by_path_and_demo_order():
    info = {
        "/i/a.png": {"width": 10, "height": 20, "exif_orientation": None},
        "/i/b.png": {"width": 30, "height": 40, "exif_orientation": None},
    }
    stdout = (
        "---Input---\nImages: ['/i/b.png', '/i/a.png']\n---Output---\n"
        "Text Output: x\nRetrieval Image: ['/i/a.png']\n"
    )

    images, source, answer_image, rule = runner.describe_images(info, stdout)

    assert source == "demo_stdout"
    assert [image["path"] for image in images] == ["/i/b.png", "/i/a.png"]
    assert images[0] == {
        "path": "/i/b.png",
        "width": 30,
        "height": 40,
        "exif_orientation": None,
        "retrieved": False,
    }
    assert images[1]["retrieved"] is True
    assert answer_image is None
    assert "Multiple images" in rule


def test_describe_images_falls_back_without_demo_output():
    info = {"/i/a.png": {"width": 10, "height": 20, "exif_orientation": None}}

    images, source, answer_image, rule = runner.describe_images(info, "")

    assert source == "wrapper_sorted_listing"
    assert images[0]["retrieved"] is None
    assert answer_image == "/i/a.png"
    assert "Single image" in rule


def test_get_repo_revision_without_git_repository(tmp_path):
    assert runner.get_repo_revision(tmp_path) == {"revision": None, "dirty": None}


def test_execute_with_fake_demo_writes_traceable_metadata(
    tmp_path, official_repo, prompt_file
):
    """Run the execute path against a stand-in demo; no model is involved."""
    answer = '[{"cls": "WBC", "box": [0.1, 0.2, 0.3, 0.4]}]'
    write_fake_demo(official_repo, answer, retrieved_index=1)
    folder = tmp_path / "images"
    folder.mkdir()
    (folder / "a.png").write_bytes(png_bytes(64, 32))
    (folder / "b.jpg").write_bytes(jpeg_bytes(100, 50))
    model = tmp_path / "mirage-checkpoint"
    model.mkdir()
    out = tmp_path / "out"

    result = run_script(
        *base_args(official_repo, folder, prompt_file, out, str(model)),
        "--max-num-retrievals",
        "1",
        "--execute",
    )

    assert result.returncode == 0, result.stderr
    assert (out / "answer.txt").read_text(encoding="utf-8") == answer
    metadata = json.loads((out / "run.json").read_text(encoding="utf-8"))

    assert metadata["image_order_source"] == "demo_stdout"
    assert [Path(i["path"]).name for i in metadata["images"]] == ["b.jpg", "a.png"]
    assert metadata["images"][0]["width"] == 100
    assert metadata["images"][0]["height"] == 50
    assert metadata["images"][0]["retrieved"] is True
    assert metadata["images"][1]["retrieved"] is False
    assert metadata["answer_image"] is None
    assert metadata["parameters"]["max_num_retrievals"] == 1
    assert metadata["parameters"]["allow_remote_model"] is False
    assert metadata["official_repo"]["revision"] is None
    assert metadata["environment"]["python"] == sys.version
    assert metadata["returncode"] == 0
    assert metadata["answer_extracted"] is True


def test_execute_single_image_associates_answer(tmp_path, official_repo, prompt_file):
    write_fake_demo(official_repo, "[]")
    folder = tmp_path / "images"
    folder.mkdir()
    (folder / "only.png").write_bytes(png_bytes(80, 60))
    model = tmp_path / "mirage-checkpoint"
    model.mkdir()
    out = tmp_path / "out"

    result = run_script(
        *base_args(official_repo, folder, prompt_file, out, str(model)), "--execute"
    )

    assert result.returncode == 0, result.stderr
    metadata = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert metadata["answer_image"] == str(folder.resolve() / "only.png")
    assert metadata["images"][0]["width"] == 80
    assert metadata["images"][0]["retrieved"] is True


@pytest.mark.parametrize(
    ("model_path", "expected"),
    [
        ("tsunghanwu/mirage-llama3.1-8.3B", "mirage-llama3.1-8.3B"),
        ("/ckpt/mirage-llama3.1-8.3B/", "mirage-llama3.1-8.3B"),
        ("/runs/llava-ft/checkpoint-500", "llava-ft_checkpoint-500"),
    ],
)
def test_official_model_name_mirrors_demo(model_path, expected):
    assert runner.official_model_name(model_path) == expected


@pytest.mark.parametrize(
    "model_path",
    [
        "/ckpt/mirage-llama3.1-8.3B",
        "/ckpt/MIRAGE",
        "tsunghanwu/mirage-llama3.1-8.3B",
        "/runs/mirage-ft/checkpoint-500",
    ],
)
def test_validate_model_name_accepts_multimodal_names(model_path):
    runner.validate_model_name(model_path)


@pytest.mark.parametrize(
    ("model_path", "message"),
    [
        ("/ckpt/model", "must contain 'mirage' or 'llava'"),
        ("/hf/snapshots/100ea29f5fb9dbd35d52390075abd9f60b225478", "must contain"),
        ("/runs/model/checkpoint-500", "must contain"),
        ("/ckpt/mirage-lora", "contains 'lora'"),
    ],
)
def test_validate_model_name_rejects_wrong_names(model_path, message):
    with pytest.raises(ValueError, match=message):
        runner.validate_model_name(model_path)


def test_dry_run_rejects_checkpoint_folder_with_wrong_name(
    tmp_path, official_repo, prompt_file
):
    folder = tmp_path / "images"
    folder.mkdir()
    (folder / "test.png").write_bytes(png_bytes(8, 8))
    model = tmp_path / "model"
    model.mkdir()

    result = run_script(
        *base_args(official_repo, folder, prompt_file, tmp_path / "out", str(model))
    )

    assert result.returncode != 0
    assert "wrong model class" in result.stderr


def write_fake_nvidia_smi(directory: Path, samples: list[int]) -> None:
    """Put a stand-in nvidia-smi on PATH: describes a GPU or streams samples."""
    lines = "".join(
        f"2026/11/18 15:00:0{i}.000, 0, {v}\n" for i, v in enumerate(samples)
    )
    script = directory / "nvidia-smi"
    script.write_text(
        f"#!{sys.executable}\n"
        "import sys, time\n"
        "if any(a.startswith('--query-gpu=name') for a in sys.argv):\n"
        "    print('Fake GPU, 24576 MiB, 550.00')\n"
        "    sys.exit(0)\n"
        f"sys.stdout.write({lines!r}); sys.stdout.flush()\n"
        "time.sleep(60)\n",
        encoding="utf-8",
    )
    script.chmod(0o755)


def execute_with_fake_demo(tmp_path, official_repo, prompt_file, env):
    write_fake_demo(official_repo, "[]")
    with (official_repo / "demo.py").open("a", encoding="utf-8") as demo:
        demo.write("import time; time.sleep(1)  # let the GPU sampler write\n")
    folder = tmp_path / "images"
    folder.mkdir()
    (folder / "a.png").write_bytes(png_bytes(8, 8))
    model = tmp_path / "mirage-checkpoint"
    model.mkdir()
    out = tmp_path / "out"
    result = run_script(
        *base_args(official_repo, folder, prompt_file, out, str(model)),
        "--execute",
        env=env,
    )
    assert result.returncode == 0, result.stderr
    return out, json.loads((out / "run.json").read_text(encoding="utf-8"))


def test_execute_records_gpu_memory_sampled_during_the_run(
    tmp_path, official_repo, prompt_file
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    write_fake_nvidia_smi(bin_dir, [500, 19800, 20100, 900])
    env = os.environ | {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                        "HF_HUB_OFFLINE": "1"}  # fmt: skip

    out, metadata = execute_with_fake_demo(tmp_path, official_repo, prompt_file, env)

    environment = metadata["environment"]
    assert environment["gpu"] == "Fake GPU, 24576 MiB, 550.00"
    assert environment["gpu_memory_log"] == "gpu-memory.csv"
    assert (out / "gpu-memory.csv").is_file()
    assert environment["gpu_memory_peak_mib"] == 20100
    assert environment["hf_hub_offline"] == "1"


def test_execute_without_nvidia_smi_records_no_gpu_memory(
    tmp_path, official_repo, prompt_file
):
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    env = {k: v for k, v in os.environ.items() if k != "HF_HUB_OFFLINE"}
    env["PATH"] = str(empty_bin)

    out, metadata = execute_with_fake_demo(tmp_path, official_repo, prompt_file, env)

    assert metadata["environment"]["gpu"] is None
    assert metadata["environment"]["gpu_memory_log"] is None
    assert metadata["environment"]["gpu_memory_peak_mib"] is None
    assert metadata["environment"]["hf_hub_offline"] is None
    assert not (out / "gpu-memory.csv").exists()


def test_read_peak_gpu_memory(tmp_path):
    log = tmp_path / "gpu.csv"
    log.write_text(
        "2026/11/18 15:00:00.000, 0, 512\n"
        "garbage line\n"
        "2026/11/18 15:00:00.500, 0, 20480\n"
        "2026/11/18 15:00:01.000, 0, [N/A]\n",
        encoding="utf-8",
    )

    assert runner.read_peak_gpu_memory_mib(log) == 20480
    assert runner.read_peak_gpu_memory_mib(tmp_path / "missing.csv") is None
