"""Run Qwen3-VL-2B-Instruct (GGUF, Q4_K_M) on one image with llama.cpp, on CPU.

Standard library only. Run from the repository root INSIDE a memory-capped scope
(the script refuses to run otherwise), so that only this process can be killed
if memory runs out and the system is not pushed into swap:

    systemd-run --user --scope -p MemoryMax=3584M -p MemorySwapMax=0 -- \
        python3 experiments/qwen3vl/run_qwen.py \
        --image /home/visioer/Downloads/BloodImage_00236.jpg \
        --output-dir experiments/qwen3vl/outputs/<run-id>

Each prompt is a separate ``llama-mtmd-cli`` process (the model is loaded every
time, so load time is measured per prompt). The full stdout (the answer) and
stderr (llama.cpp logs and timings) are saved untouched, together with memory
samples, hashes and parameters. Nothing here parses or converts the answers.
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
LLAMA_RELEASE = "b12119"
LLAMA_COMMIT = "6f1e6543704bc5b080c7a98e7b6f707b31f6ed51"
LLAMA_DIR = HERE / "bin" / f"llama-{LLAMA_RELEASE}"
MODEL_REPO = "Qwen/Qwen3-VL-2B-Instruct-GGUF"
MODEL_REVISION = "52d6c8ffea26cc873ac5ad116f8631268d7eb503"
MODEL_FILE = HERE / "models" / "Qwen3VL-2B-Instruct-Q4_K_M.gguf"
MMPROJ_FILE = HERE / "models" / "mmproj-Qwen3VL-2B-Instruct-F16.gguf"
EXPECTED_SHA256 = {
    MODEL_FILE.name: "089d75c52f4b7ffc56ba998ffc50aae89fcafc755f9e7208aacca281dca6c2ae",
    MMPROJ_FILE.name: "c3d5afbef5287953acd57b4043d2269456e5761a4eaccb3b71b062996970aea5",
}
# Grounding prompts follow the official Qwen3-VL 2D grounding cookbook wording.
GROUNDING = (
    'Locate every instance that belongs to the following categories: "{}". '
    "Report bbox coordinates in JSON format."
)
PROMPTS = [
    ("describe", "Describe this image briefly."),
    ("ground_rbc", GROUNDING.format("red blood cell")),
    ("ground_wbc", GROUNDING.format("white blood cell")),
    ("ground_platelet", GROUNDING.format("platelet")),
    ("ground_all", GROUNDING.format("red blood cell, white blood cell, platelet")),
]
# Shared by every configuration: -c 4096 is required (the default, 0, would use
# the model's 256K context); fixed seed, output limit and threads.
BASE = ["--seed", "42", "-n", "1024", "-c", "4096", "-t", "10"]
# First run (2026-11-18): greedy decoding with llama.cpp's other sampler defaults.
GREEDY = ["--temp", "0"]
# Official Qwen3-VL "VL" generation hyperparameters (GGUF README): sampling with
# temperature 0.7, top_p 0.8, top_k 20, repetition_penalty 1.0 and
# presence_penalty 1.5. min-p is not part of them; llama.cpp's own default
# (0.05) is disabled so that only the official samplers act.
OFFICIAL_SAMPLING = [
    "--temp", "0.7", "--top-p", "0.8", "--top-k", "20", "--min-p", "0",
    "--repeat-penalty", "1.0", "--presence-penalty", "1.5",
]  # fmt: skip
# llama.cpp warns that Qwen-VL grounding needs at least 1024 image tokens.
IMAGE_1024 = ["--image-min-tokens", "1024"]
# Each configuration changes one variable (sampling or image tokens) at a time.
CONFIGS = {
    "original": GREEDY + BASE,
    "tokens1024": GREEDY + IMAGE_1024 + BASE,
    "official_sampling": OFFICIAL_SAMPLING + BASE,
    "combined": OFFICIAL_SAMPLING + IMAGE_1024 + BASE,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def meminfo() -> dict[str, int]:
    """MemAvailable, SwapTotal and SwapFree of the system, in MiB."""
    values = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, _, rest = line.partition(":")
        if key in ("MemAvailable", "SwapTotal", "SwapFree"):
            values[key] = int(rest.split()[0]) // 1024
    return values


def cgroup_dir() -> Path:
    return Path(
        "/sys/fs/cgroup" + Path("/proc/self/cgroup").read_text().split(":")[-1].strip()
    )


def read_cgroup(name: str) -> str | None:
    path = cgroup_dir() / name
    return path.read_text().strip() if path.is_file() else None


def sample_process(pid: int, samples: dict[str, int], stop: threading.Event) -> None:
    """Track peak VmRSS and VmSwap (KiB) of a running process."""
    while not stop.is_set():
        try:
            lines = Path(f"/proc/{pid}/status").read_text().splitlines()
        except OSError:
            break
        for line in lines:
            if line.startswith(("VmRSS:", "VmSwap:", "VmHWM:")):
                key = line.split(":")[0]
                samples[key] = max(samples.get(key, 0), int(line.split()[1]))
        stop.wait(0.1)


def build_command(prompt: str, image: Path, config: str) -> list[str]:
    """Return the llama-mtmd-cli command for one prompt and configuration."""
    return [
        str(LLAMA_DIR / "llama-mtmd-cli"),
        "-m", str(MODEL_FILE), "--mmproj", str(MMPROJ_FILE),
        "--image", str(image), "-p", prompt, *CONFIGS[config],
    ]  # fmt: skip


def run_prompt(
    name: str, prompt: str, image: Path, out: Path, config: str
) -> dict[str, object]:
    command = build_command(prompt, image, config)
    env = os.environ | {"LD_LIBRARY_PATH": str(LLAMA_DIR)}
    before = meminfo()
    started = time.perf_counter()
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
    )
    samples: dict[str, int] = {}
    stop = threading.Event()
    sampler = threading.Thread(target=sample_process, args=(process.pid, samples, stop))
    sampler.start()
    stdout, stderr = process.communicate()
    wall = time.perf_counter() - started
    stop.set()
    sampler.join()
    after = meminfo()
    (out / f"{name}.stdout.txt").write_bytes(stdout)
    (out / f"{name}.stderr.txt").write_bytes(stderr)
    return {
        "name": name,
        "prompt": prompt,
        "command": command,
        "returncode": process.returncode,
        "wall_seconds": round(wall, 3),
        "stdout_file": f"{name}.stdout.txt",
        "stderr_file": f"{name}.stderr.txt",
        "answer": stdout.decode("utf-8", errors="replace"),
        "process_peak_mib": {k: round(v / 1024, 1) for k, v in samples.items()},
        "system_before_mib": before,
        "system_after_mib": after,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", choices=CONFIGS, default="original")
    parser.add_argument(
        "--prompts",
        nargs="+",
        choices=[name for name, _ in PROMPTS],
        help="subset of prompts to run (default: all)",
    )
    args = parser.parse_args(argv)
    selected = [(n, p) for n, p in PROMPTS if not args.prompts or n in args.prompts]

    memory_max = read_cgroup("memory.max")
    if memory_max in (None, "max") or read_cgroup("memory.swap.max") != "0":
        print("Run inside a scope with MemoryMax and MemorySwapMax=0 (see docstring).")
        return 2
    hashes = {path.name: sha256(path) for path in (MODEL_FILE, MMPROJ_FILE)}
    if hashes != EXPECTED_SHA256:
        print(f"GGUF files differ from the published hashes: {hashes}")
        return 2

    started_at = datetime.now(UTC).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for name, prompt in selected:
        result = run_prompt(name, prompt, args.image, args.output_dir, args.config)
        results.append(result)
        print(f"{name}: returncode {result['returncode']}, {result['wall_seconds']} s")
        if result["returncode"] != 0:
            print("Stopping: a run failed (see its stderr).")
            break

    run = {
        "started_at": started_at,
        "created_at": datetime.now(UTC).isoformat(),
        "runtime": {
            "llama_cpp_release": LLAMA_RELEASE,
            "llama_cpp_commit": LLAMA_COMMIT,
            "asset": f"llama-{LLAMA_RELEASE}-bin-ubuntu-x64.tar.gz",
            "device": "cpu",
        },
        "model": {
            "repo": MODEL_REPO,
            "revision": MODEL_REVISION,
            "files_sha256": hashes,
        },
        "image": {"path": str(args.image), "sha256": sha256(args.image)},
        "config": args.config,
        "generation": CONFIGS[args.config],
        "memory_limit": {
            "memory.max": memory_max,
            "memory.swap.max": read_cgroup("memory.swap.max"),
            "cgroup_memory_peak_bytes": read_cgroup("memory.peak"),
            "oom_events": read_cgroup("memory.events"),
        },
        "environment": {"python": sys.version, "platform": platform.platform()},
        "prompts": results,
    }
    (args.output_dir / "run.json").write_text(
        json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Saved {args.output_dir / 'run.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
