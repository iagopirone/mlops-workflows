"""Run an opt-in MIRAGE experiment using the official demo in an isolated environment.

By default this tool only validates inputs and prints the command. It does not
import MIRAGE, install dependencies, download weights, or perform inference.

The script uses only the standard library and must stay compatible with
Python 3.10, the version of the official MIRAGE environment.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import platform
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp"}

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# JPEG start-of-frame markers (excluding DHT 0xC4, JPG 0xC8 and DAC 0xCC).
JPEG_SOF_MARKERS = {
    0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
}  # fmt: skip

SINGLE_IMAGE_RULE = (
    "Single image: the answer and any coordinates in it refer to this image."
)
# The official builder only loads the multimodal model when the model name
# (derived from the path) contains one of these, and treats "lora" specially.
MULTIMODAL_NAME_KEYS = ("llava", "mirage")


def official_model_name(model_path: str) -> str:
    """Return the name the official demo derives from --model-path.

    Mirrors ``get_model_name_from_path`` in ``llava/mm_utils.py`` (commit 617751c).
    """
    parts = model_path.strip("/").split("/")
    if parts[-1].startswith("checkpoint-"):
        return parts[-2] + "_" + parts[-1]
    return parts[-1]


def validate_model_name(model_path: str) -> None:
    """Reject paths whose name would make the official demo load the wrong model.

    Without "llava" or "mirage" in the name the builder silently loads a plain
    language model; with "lora" it expects a base model that demo.py never passes.
    """
    name = official_model_name(model_path).lower()
    if not any(key in name for key in MULTIMODAL_NAME_KEYS):
        raise ValueError(
            f"Model name {name!r} (last path segment) must contain 'mirage' or "
            "'llava'; otherwise the official builder loads the wrong model class. "
            "Rename the checkpoint folder, e.g. mirage-llama3.1-8.3B."
        )
    if "lora" in name:
        raise ValueError(
            f"Model name {name!r} contains 'lora'; demo.py passes no base model, "
            "so the official builder cannot load it."
        )


MULTIPLE_IMAGES_RULE = (
    "Multiple images: MIRAGE output does not identify which image a statement "
    "or box refers to. Do not convert coordinates from this answer."
)


def read_image_info(path: Path) -> dict[str, int | None]:
    """Read the stored width, height and EXIF orientation from the file header.

    MIRAGE opens images with PIL, which does not apply EXIF orientation, so the
    stored size is the one the model sees. Supported formats: PNG, JPEG, BMP.
    """
    data = path.read_bytes()

    if data.startswith(PNG_SIGNATURE) and data[12:16] == b"IHDR":
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        orientation = None
    elif data.startswith(b"\xff\xd8"):
        width, height, orientation = _read_jpeg_info(data)
    elif data.startswith(b"BM") and len(data) >= 26:
        width, height = _read_bmp_size(data)
        orientation = None
    else:
        raise ValueError(f"Unsupported or unreadable image header: {path}")

    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid image dimensions in: {path}")

    return {"width": width, "height": height, "exif_orientation": orientation}


def _read_jpeg_info(data: bytes) -> tuple[int, int, int | None]:
    """Return width, height and EXIF orientation of a JPEG file."""
    index = 2
    size = None
    orientation = None

    while index + 4 <= len(data):
        if data[index] != 0xFF:
            raise ValueError("Invalid JPEG marker.")

        marker = data[index + 1]

        if marker == 0xFF:  # Fill byte.
            index += 1
            continue

        if marker == 0x01 or 0xD0 <= marker <= 0xD7:  # Markers without length.
            index += 2
            continue

        if marker in (0xD9, 0xDA):  # End of image or start of scan data.
            break

        length = int.from_bytes(data[index + 2 : index + 4], "big")
        segment = data[index + 4 : index + 2 + length]

        if marker == 0xE1 and segment.startswith(b"Exif\x00\x00"):
            orientation = _read_exif_orientation(segment[6:])
        elif marker in JPEG_SOF_MARKERS and len(segment) >= 5:
            height = int.from_bytes(segment[1:3], "big")
            width = int.from_bytes(segment[3:5], "big")
            size = (width, height)

        index += 2 + length

    if size is None:
        raise ValueError("JPEG frame header not found.")

    return size[0], size[1], orientation


def _read_exif_orientation(tiff: bytes) -> int | None:
    """Return the orientation tag (0x0112) of the first EXIF IFD, if present."""
    byte_order = {b"II": "little", b"MM": "big"}.get(tiff[:2])

    if byte_order is None or len(tiff) < 8:
        return None

    offset = int.from_bytes(tiff[4:8], byte_order)

    if offset + 2 > len(tiff):
        return None

    count = int.from_bytes(tiff[offset : offset + 2], byte_order)

    for entry in range(count):
        start = offset + 2 + 12 * entry

        if start + 12 > len(tiff):
            break

        if int.from_bytes(tiff[start : start + 2], byte_order) == 0x0112:
            return int.from_bytes(tiff[start + 8 : start + 10], byte_order)

    return None


def _read_bmp_size(data: bytes) -> tuple[int, int]:
    """Return width and height of a BMP file (top-down height is negative)."""
    header_size = int.from_bytes(data[14:18], "little")

    if header_size == 12:  # OS/2 BITMAPCOREHEADER.
        return (
            int.from_bytes(data[18:20], "little"),
            int.from_bytes(data[20:22], "little"),
        )

    width = int.from_bytes(data[18:22], "little", signed=True)
    height = int.from_bytes(data[22:26], "little", signed=True)
    return width, abs(height)


def extract_text_output(stdout: str) -> str | None:
    """Extract the displayed text answer without interpreting its meaning.

    Return None if the official demo output markers are not found. The original
    stdout is always saved separately on execution.
    """
    if "---Output---" not in stdout:
        return None
    output = stdout.rsplit("---Output---", 1)[1]
    if "Text Output:" not in output:
        return None
    answer = output.split("Text Output:", 1)[1]
    # The demo prints the retrieval line last, so split on its last occurrence.
    if "Retrieval Image:" in answer:
        answer = answer.rsplit("Retrieval Image:", 1)[0]
    return answer.strip()


def extract_printed_list(stdout: str, label: str) -> list[str] | None:
    """Return the Python list printed by the demo after ``label``, if any.

    ``Images:`` is read from the input section and ``Retrieval Image:`` from
    the output section; the last matching line is used.
    """
    if "---Output---" not in stdout:
        return None

    before, after = stdout.rsplit("---Output---", 1)
    section = after if label == "Retrieval Image:" else before
    lines = [line for line in section.splitlines() if line.startswith(label)]

    if not lines:
        return None

    try:
        value = ast.literal_eval(lines[-1][len(label) :].strip())
    except (ValueError, SyntaxError):
        return None

    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        return None

    return value


def get_repo_revision(repo: Path) -> dict[str, object]:
    """Return the Git commit and dirty state of the official repository."""
    try:
        revision = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return {"revision": None, "dirty": None}

    return {"revision": revision, "dirty": bool(status.strip())}


def get_gpu_description() -> str | None:
    """Describe available NVIDIA GPUs, or return None if unavailable."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    return result.stdout.strip() or None


def start_gpu_monitor(path: Path) -> subprocess.Popen[bytes] | None:
    """Sample GPU memory every 500 ms into ``path`` while the demo runs.

    Returns None when ``nvidia-smi`` is unavailable (no file is kept).
    """
    with path.open("wb") as handle:
        try:
            return subprocess.Popen(
                [
                    "nvidia-smi",
                    "--query-gpu=timestamp,index,memory.used",
                    "--format=csv,noheader,nounits",
                    "-lms",
                    "500",
                ],
                stdout=handle,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass
    path.unlink()
    return None


def stop_gpu_monitor(process: subprocess.Popen[bytes] | None) -> None:
    """Stop the GPU memory sampler, if it is running."""
    if process is None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def read_peak_gpu_memory_mib(path: Path) -> int | None:
    """Return the highest ``memory.used`` sample (MiB) in a monitor file."""
    if not path.is_file():
        return None
    peak = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        value = line.rsplit(",", 1)[-1].strip()
        if value.isdigit():
            peak = max(peak or 0, int(value))
    return peak


def describe_images(
    image_info: dict[str, dict[str, int | None]],
    stdout: str,
) -> tuple[list[dict[str, object]], str, str | None, str]:
    """Relate images to the demo order, retrieval output and the answer.

    Images are matched by path, never by position, because the demo uses
    ``os.listdir`` order, which may differ from the sorted listing.
    """
    demo_order = extract_printed_list(stdout, "Images:")

    if demo_order is not None and sorted(demo_order) == sorted(image_info):
        order, order_source = demo_order, "demo_stdout"
    else:
        order, order_source = list(image_info), "wrapper_sorted_listing"

    retrieved = extract_printed_list(stdout, "Retrieval Image:")
    images = [
        {
            "path": path,
            **image_info[path],
            "retrieved": None if retrieved is None else path in retrieved,
        }
        for path in order
    ]

    if len(images) == 1:
        return images, order_source, images[0]["path"], SINGLE_IMAGE_RULE

    return images, order_source, None, MULTIPLE_IMAGES_RULE


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare or execute the official MIRAGE demo and capture raw output."
        )
    )
    parser.add_argument("--official-repo", type=Path, required=True)
    parser.add_argument("--image-folder", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-num-retrievals", type=int, default=1)
    parser.add_argument(
        "--execute", action="store_true", help="Actually launch the official demo."
    )
    parser.add_argument(
        "--allow-remote-model",
        action="store_true",
        help="Allow an HF model ID that may trigger a large download (with --execute).",
    )
    return parser


def validate_inputs(
    args: argparse.Namespace,
) -> tuple[dict[str, dict[str, int | None]], str, Path, Path]:
    """Validate inputs and return image info by path, prompt, repo and folder."""
    repo = args.official_repo.expanduser().resolve()
    images_dir = args.image_folder.expanduser().resolve()
    prompt_file = args.prompt_file.expanduser().resolve()

    if not (repo / "demo.py").is_file():
        raise ValueError(f"Official MIRAGE demo.py not found in: {repo}")
    if not images_dir.is_dir():
        raise ValueError(f"Image folder not found: {images_dir}")
    entries = sorted(images_dir.iterdir())
    if not entries:
        raise ValueError("Image folder is empty.")
    if any(not p.is_file() or p.suffix.lower() not in IMAGE_SUFFIXES for p in entries):
        raise ValueError(
            "The official demo reads every entry in --image-folder. "
            "Use a dedicated folder containing only supported image files "
            f"({', '.join(sorted(IMAGE_SUFFIXES))})."
        )

    image_info = {}
    for path in entries:
        info = read_image_info(path)
        if info["exif_orientation"] not in (None, 1):
            raise ValueError(
                f"{path.name} has EXIF orientation {info['exif_orientation']}. "
                "MIRAGE (PIL) ignores it but the project (OpenCV) applies it, so "
                "coordinates would refer to different pixel grids. "
                "Save the image without EXIF rotation first."
            )
        # Same string the demo builds with os.path.join(image_folder, name).
        image_info[str(path)] = info

    if not prompt_file.is_file():
        raise ValueError(f"Prompt file not found: {prompt_file}")
    prompt = prompt_file.read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError("Prompt must not be empty.")
    if args.max_num_retrievals < 1:
        raise ValueError("--max-num-retrievals must be at least 1.")
    if args.max_num_retrievals > len(entries):
        raise ValueError("--max-num-retrievals cannot exceed the image count.")
    if args.execute and not args.allow_remote_model:
        checkpoint = Path(args.model_path).expanduser()
        if not checkpoint.exists():
            raise ValueError(
                "Model path does not exist locally. Remote model IDs may download "
                "weights; use --allow-remote-model only if you authorize that."
            )
    return image_info, prompt, repo, images_dir


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        image_info, prompt, repo, images_dir = validate_inputs(args)
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))

    checkpoint = Path(args.model_path).expanduser()
    model_path = str(checkpoint.resolve()) if checkpoint.exists() else args.model_path
    try:
        validate_model_name(model_path)
    except ValueError as exc:
        parser.error(str(exc))
    command = [
        sys.executable,
        str(repo / "demo.py"),
        "--model-path",
        model_path,
        "--image-folder",
        str(images_dir),
        "--prompt",
        prompt,  # Official demo accepts literal prompt text, not a file path.
        "--max-num-retrievals",
        str(args.max_num_retrievals),
    ]
    repo_info = get_repo_revision(repo)

    print(f"Images: {len(image_info)}")
    for path, info in image_info.items():
        print(f"  {path}: {info['width']}x{info['height']}")
    print(f"Official repo revision: {repo_info['revision'] or 'unknown'}")
    print(f"Answer association: {describe_images(image_info, '')[3]}")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN (default)'}")
    print(f"Command: {shlex.join(command)}")

    if not args.execute:
        print("No model executed; no weights downloaded; no output files created.")
        return 0

    # Execute only when explicitly approved and run on a compatible GPU host.
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    gpu_log = output_dir / "gpu-memory.csv"
    monitor = start_gpu_monitor(gpu_log)
    started_at = datetime.now(timezone.utc)
    try:
        result = subprocess.run(
            command, cwd=repo, capture_output=True, text=True, check=False
        )
    finally:
        finished_at = datetime.now(timezone.utc)
        stop_gpu_monitor(monitor)

    (output_dir / "stdout.txt").write_text(result.stdout, encoding="utf-8")
    (output_dir / "stderr.txt").write_text(result.stderr, encoding="utf-8")
    answer = extract_text_output(result.stdout)
    if answer is not None:
        (output_dir / "answer.txt").write_text(answer, encoding="utf-8")

    images, order_source, answer_image, answer_rule = describe_images(
        image_info, result.stdout
    )
    metadata = {
        "experiment": "mirage-official-demo",
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
        "parameters": {
            "model_path": args.model_path,
            "model_path_resolved": model_path,
            "image_folder": str(images_dir),
            "prompt_file": str(args.prompt_file.expanduser().resolve()),
            "max_num_retrievals": args.max_num_retrievals,
            "allow_remote_model": args.allow_remote_model,
        },
        "prompt": prompt,
        "command": command,
        "official_repo": {"path": str(repo), **repo_info},
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "gpu": get_gpu_description(),
            "hf_hub_offline": os.environ.get("HF_HUB_OFFLINE"),
            "gpu_memory_log": gpu_log.name if gpu_log.is_file() else None,
            "gpu_memory_peak_mib": read_peak_gpu_memory_mib(gpu_log),
        },
        "image_count": len(images),
        "image_order_source": order_source,
        "images": images,
        "answer_image": answer_image,
        "answer_image_rule": answer_rule,
        "image_size_note": (
            "width/height are the stored pixel dimensions (EXIF rotation is "
            "rejected), i.e. the size PIL gives to MIRAGE before padding."
        ),
        "returncode": result.returncode,
        "answer_extracted": answer is not None,
        "warning": (
            "Text output is not verified detection data; do not use as "
            "DetectionContent without separate validation."
        ),
    }
    (output_dir / "run.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Exit code: {result.returncode}")
    print(f"Raw outputs and metadata: {output_dir}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
