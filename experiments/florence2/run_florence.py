"""Run the official Florence-2-base-ft tasks on one image, on CPU, and save everything.

Runs ONLY in the isolated environment (``experiments/florence2/.venv``), from
the repository root:

    HF_HUB_OFFLINE=1 experiments/florence2/.venv/bin/python \
        experiments/florence2/run_florence.py \
        --image /home/visioer/Downloads/BloodImage_00236.jpg \
        --output-dir experiments/florence2/outputs/<run-id>

The model is loaded from the local, pinned and reviewed snapshot
(``models/Florence-2-base-ft``) with ``trust_remote_code=True``; the remote
code files are hash-checked before loading. Nothing here converts or draws
detections: that is done in the project environment by ``render.py``.
"""

import argparse
import hashlib
import json
import os
import platform
import resource
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

MODEL_ID = "microsoft/Florence-2-base-ft"
MODEL_REVISION = "f6c1a25888ffc1d945ee8a1a77ac833c7303d46e"
MODEL_DIR = Path(__file__).resolve().parent / "models" / "Florence-2-base-ft"
# SHA-256 of the files reviewed on 2026-11-18 (remote code) and published (weights).
EXPECTED_SHA256 = {
    "configuration_florence2.py": "653bafddc9651eaff1583a16db4a2bb27d33ec7d541dfab7201aaa4ecaa1cfbf",
    "modeling_florence2.py": "5bb7aa72c6ba62e96e1bbae6bc1aaf7b4e8e28cdfc62e670de3d5b67eeab1fdf",
    "processing_florence2.py": "4bd7158536cbf1c7891fc8efd94437d79fd09f07f539c7398fab8a885d7d8bca",
    "model.safetensors": "58757d657ff44051314c8030b68e04cb1bb618ca9a4885418f111f6fb708185a",
}
# Official task tokens; grounding takes the phrase right after the token.
TASKS = [
    ("<OD>", None),
    ("<CAPTION_TO_PHRASE_GROUNDING>", "red blood cells"),
    ("<CAPTION_TO_PHRASE_GROUNDING>", "white blood cells"),
    ("<CAPTION_TO_PHRASE_GROUNDING>", "platelets"),
]
# Generation settings of the official README example.
# use_cache=False: with transformers 4.55 the remote code fails inside generate
# ("Cache only has 0 layers"); without the KV cache the decoder recomputes past
# tokens, which is slower but does not change the decoding algorithm.
GENERATION = {
    "max_new_tokens": 1024,
    "num_beams": 3,
    "do_sample": False,
    "use_cache": False,
}
ATTENTION = "eager"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def memory_mib() -> dict[str, float]:
    """Current and peak resident memory of this process, in MiB."""
    status = Path("/proc/self/status").read_text().splitlines()
    rss_kib = next(int(line.split()[1]) for line in status if line.startswith("VmRSS:"))
    peak_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {
        "rss_mib": round(rss_kib / 1024, 1),
        "peak_rss_mib": round(peak_kib / 1024, 1),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    # Keep the copy of the remote code that transformers makes inside the experiment.
    os.environ.setdefault("HF_MODULES_CACHE", str(MODEL_DIR.parent / ".modules"))
    if os.environ.get("HF_HUB_OFFLINE") != "1":
        print("Set HF_HUB_OFFLINE=1: the model must load from the local snapshot.")
        return 2
    hashes = {name: sha256(MODEL_DIR / name) for name in EXPECTED_SHA256}
    if hashes != EXPECTED_SHA256:
        print(f"Model files differ from the reviewed ones: {hashes}")
        return 2

    started = time.perf_counter()
    import timm
    import torch
    import transformers
    from PIL import Image
    from transformers import AutoModelForCausalLM, AutoProcessor

    import_seconds = time.perf_counter() - started
    memory_after_imports = memory_mib()

    image = Image.open(args.image)
    exif_orientation = image.getexif().get(274)
    image = image.convert("RGB")

    started = time.perf_counter()
    # "eager": with transformers 4.55 the remote code's _supports_sdpa property
    # reads self.language_model before it exists (AttributeError); asking for
    # the plain PyTorch attention skips that check without editing the code.
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_DIR,
        torch_dtype=torch.float32,
        trust_remote_code=True,
        attn_implementation=ATTENTION,
    ).eval()
    processor = AutoProcessor.from_pretrained(MODEL_DIR, trust_remote_code=True)
    load_seconds = time.perf_counter() - started
    memory_after_load = memory_mib()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for index, (task, phrase) in enumerate(TASKS):
        prompt = task + (phrase or "")
        record = {"index": index, "task": task, "phrase": phrase, "prompt": prompt}
        try:
            inputs = processor(text=prompt, images=image, return_tensors="pt")
            started = time.perf_counter()
            with torch.inference_mode():
                generated_ids = model.generate(
                    input_ids=inputs["input_ids"],
                    pixel_values=inputs["pixel_values"],
                    **GENERATION,
                )
            record["inference_seconds"] = round(time.perf_counter() - started, 3)
            raw = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
            parsed = processor.post_process_generation(
                raw, task=task, image_size=(image.width, image.height)
            )
            raw_file = args.output_dir / f"task-{index}-raw.txt"
            raw_file.write_text(raw, encoding="utf-8")
            record |= {
                "status": "completed",
                "raw_output_file": raw_file.name,
                "raw_output": raw,
                "parsed": parsed,
                "generated_tokens": int(generated_ids.shape[-1]),
            }
        except Exception as exc:  # noqa: BLE001 - record any failure as a result
            record |= {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
        record["memory_after"] = memory_mib()
        results.append(record)
        print(f"{prompt}: {record['status']} {record.get('inference_seconds')} s")

    run = {
        "created_at": datetime.now(UTC).isoformat(),
        "model": {
            "id": MODEL_ID,
            "revision": MODEL_REVISION,
            "local_dir": str(MODEL_DIR),
            "files_sha256": hashes,
            "trust_remote_code": True,
            "dtype": "float32",
            "attn_implementation": ATTENTION,
            "device": "cpu",
        },
        "image": {
            "path": str(args.image),
            "sha256": sha256(args.image),
            "width": image.width,
            "height": image.height,
            "exif_orientation": exif_orientation,
        },
        "generation": GENERATION,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "timm": timm.__version__,
            "torch_threads": torch.get_num_threads(),
            "hf_hub_offline": os.environ.get("HF_HUB_OFFLINE"),
            "hf_modules_cache": os.environ.get("HF_MODULES_CACHE"),
        },
        "timing_seconds": {
            "imports": round(import_seconds, 3),
            "model_load": round(load_seconds, 3),
        },
        "memory": {
            "after_imports": memory_after_imports,
            "after_load": memory_after_load,
        },
        "peak_rss_mib": memory_mib()["peak_rss_mib"],
        "tasks": results,
    }
    (args.output_dir / "run.json").write_text(
        json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Saved {args.output_dir / 'run.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
