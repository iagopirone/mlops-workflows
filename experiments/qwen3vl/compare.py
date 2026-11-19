"""Compare Qwen3-VL runs (configurations) prompt by prompt, read-only.

Runs in the project environment, from the repository root, after ``render.py``
was run on each run directory:

    uv run python -m experiments.qwen3vl.compare \
        experiments/qwen3vl/outputs/<run-a> experiments/qwen3vl/outputs/<run-b> ...

For every prompt of every run it reports time, memory, swap, the render status
(JSON validity), the number of raw boxes, exact duplicate boxes, raw labels and
the converted boxes. Raw boxes and labels are read from the original answer
text, also when the JSON is broken, only to describe it; nothing is corrected.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from experiments.mirage.evaluate_detections import box_iou

_NUM = r"\s*(-?\d+(?:\.\d+)?)\s*"
RAW_BOX = re.compile(r'"bbox_2d"\s*:\s*\[' + ",".join([_NUM] * 4) + r"\]")
RAW_LABEL = re.compile(r'"label"\s*:\s*"([^"]*)"')
RAW_ITEM = re.compile(
    r'"bbox_2d"\s*:\s*\[' + ",".join([_NUM] * 4) + r'\]\s*,\s*"label"\s*:\s*"([^"]*)"'
)
# Same-label boxes overlapping this much are counted as near-duplicates.
NEAR_DUPLICATE_IOU = 0.5


def near_duplicate_pairs(answer: str) -> int:
    """Pairs of distinct same-label boxes with IoU >= NEAR_DUPLICATE_IOU."""
    items = [
        ([float(v) for v in m.groups()[:4]], m.group(5))
        for m in RAW_ITEM.finditer(answer)
    ]
    return sum(
        1
        for i, (box_a, label_a) in enumerate(items)
        for box_b, label_b in items[i + 1 :]
        if label_a == label_b
        and box_a != box_b
        and box_iou(box_a, box_b) >= NEAR_DUPLICATE_IOU
    )


def raw_boxes(answer: str) -> list[tuple[float, ...]]:
    """Well-formed ``bbox_2d`` lists found in the answer text, in order."""
    return [tuple(float(v) for v in m.groups()) for m in RAW_BOX.finditer(answer)]


def describe_answer(answer: str) -> dict[str, object]:
    """Count boxes, exact duplicates and labels written in an answer."""
    boxes = raw_boxes(answer)
    counts = Counter(boxes)
    return {
        "raw_boxes": len(boxes),
        "unique_boxes": len(counts),
        "duplicate_boxes": len(boxes) - len(counts),
        "max_repeats_of_one_box": max(counts.values(), default=0),
        "near_duplicate_pairs_iou50": near_duplicate_pairs(answer),
        "raw_labels": dict(Counter(RAW_LABEL.findall(answer))),
    }


def compare(run_dirs: list[Path]) -> list[dict[str, object]]:
    rows = []
    for run_dir in run_dirs:
        run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        summary_file = run_dir / "summary.json"
        summary = (
            json.loads(summary_file.read_text(encoding="utf-8"))
            if summary_file.is_file()
            else {"prompts": []}
        )
        statuses = {p["name"]: p for p in summary["prompts"]}
        peak = run["memory_limit"].get("cgroup_memory_peak_bytes")
        for prompt in run["prompts"]:
            answer = (run_dir / prompt["stdout_file"]).read_text(encoding="utf-8")
            rendered = statuses.get(prompt["name"], {})
            rows.append(
                {
                    "run": run_dir.name,
                    "config": run.get("config", "original"),
                    "prompt": prompt["name"],
                    "returncode": prompt["returncode"],
                    "wall_seconds": prompt["wall_seconds"],
                    "process_peak_mib": prompt["process_peak_mib"],
                    "run_cgroup_peak_gib": round(int(peak) / 2**30, 2)
                    if peak
                    else None,
                    "status": rendered.get("status"),
                    "error": rendered.get("error"),
                    "detections": rendered.get("detections", []),
                    "annotated_image": rendered.get("annotated_image"),
                    **describe_answer(answer),
                }
            )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dirs", type=Path, nargs="+")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    rows = compare(args.run_dirs)
    text = json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    for row in rows:
        print(
            f"{row['run']:32} {row['prompt']:16} {row['status']!s:15} "
            f"{row['wall_seconds']:7.1f}s boxes={row['raw_boxes']:3} "
            f"dup={row['duplicate_boxes']:3} near={row['near_duplicate_pairs_iou50']:3} "
            f"labels={row['raw_labels']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
