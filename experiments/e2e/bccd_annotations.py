"""Convert BCCD Pascal VOC annotations into the offline evaluator's format.

Run from the repository root, in the project environment, BEFORE any model
prediction is produced or looked at:

    uv run python -m experiments.e2e.bccd_annotations \
        --voc-root /data/BCCD_Dataset/BCCD --image-list test.txt --limit 20 \
        --pixel-origin one --output-dir outputs/e2e/annotations \
        [--exclude-ids seed_ids.txt --exclude-reason "possible YOLO training image"]

Selection is deterministic: candidates are the split's image IDs sorted
alphabetically; the first LIMIT eligible ones are selected. An image is
ineligible when it is listed in ``--exclude-ids``, has missing or invalid
files/annotations, or has suspicious duplicate boxes; it is skipped and replaced
by the next eligible candidate. Annotations are never corrected and the dataset
files are only read. ``selection.json`` records the candidate list, every
exclusion with its reason and hashes, the substitutions and the selected images.
"""

import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from experiments.mirage.evaluate_detections import box_iou
from experiments.mirage.run_poc import read_image_info
from mlops_workflows.components.text_detection_parsing.text_detection_parser import (
    TextDetectionParser,
)

CLASSES = ("RBC", "WBC", "Platelets")
PIXEL_ORIGINS = ("one", "zero")
# Two boxes of the same class overlapping this much are treated as a suspicious
# duplicate annotation (two distinct cells practically never overlap this much).
DUPLICATE_IOU = 0.95
SELECTION_RULE = (
    "Candidates are the split's image IDs sorted alphabetically; the first LIMIT "
    "eligible images are selected. Ineligible images (excluded IDs, missing or "
    "invalid files or annotations, suspicious duplicate boxes) are skipped and "
    "replaced by the next eligible candidate. Done before any prediction."
)


class IneligibleImageError(ValueError):
    """An image that cannot be used for evaluation, with the reason."""


def sha256(path: Path) -> str:
    """Return the SHA-256 of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def list_image_ids(list_file: Path) -> list[str]:
    """Return the unique image IDs of a VOC split file, sorted."""
    text = list_file.read_text(encoding="utf-8")
    return sorted({line.strip() for line in text.split("\n")} - {""})


def _number(node: ET.Element, tag: str, source: str) -> float:
    text = node.findtext(tag)
    if text is None:
        raise ValueError(f"{source}: missing <{tag}>.")
    return float(text)


def read_voc(xml_path: Path, pixel_origin: str) -> dict[str, object]:
    """Read one VOC file into pixel boxes ``[x1, y1, x2, y2]`` of a continuous grid.

    With ``pixel_origin="one"`` (VOC convention) pixel ``i`` covers
    ``[i - 1, i]``, so ``xmin`` and ``ymin`` are shifted by one; with ``"zero"``
    the values are used as they are. The caller must confirm the convention.
    """
    if pixel_origin not in PIXEL_ORIGINS:
        raise ValueError(f"Unsupported pixel origin: {pixel_origin!r}")
    source = xml_path.name
    root = ET.parse(xml_path).getroot()
    size = root.find("size")
    if size is None:
        raise ValueError(f"{source}: missing <size>.")
    width, height = (int(_number(size, tag, source)) for tag in ("width", "height"))
    shift = 1.0 if pixel_origin == "one" else 0.0

    objects = []
    for node in root.iter("object"):
        cls = (node.findtext("name") or "").strip()
        if cls not in CLASSES:
            raise ValueError(f"{source}: unknown class {cls!r}; expected {CLASSES}.")
        box = node.find("bndbox")
        if box is None:
            raise ValueError(f"{source}: object without <bndbox>.")
        x1, y1, x2, y2 = (
            _number(box, tag, source) for tag in ("xmin", "ymin", "xmax", "ymax")
        )
        objects.append({"cls": cls, "box": [x1 - shift, y1 - shift, x2, y2]})

    return {
        "filename": (root.findtext("filename") or "").strip(),
        "width": width,
        "height": height,
        "objects": objects,
    }


def find_duplicates(objects: list[dict[str, object]]) -> list[str]:
    """Describe pairs of same-class boxes with IoU >= ``DUPLICATE_IOU``."""
    found = []
    for i, first in enumerate(objects):
        for j in range(i + 1, len(objects)):
            second = objects[j]
            if first["cls"] != second["cls"]:
                continue
            iou = box_iou(first["box"], second["box"])
            if iou >= DUPLICATE_IOU:
                found.append(f"objects {i} and {j} ({first['cls']}, IoU {iou:.3f})")
    return found


def _hashes(xml_path: Path, image_path: Path) -> dict[str, str | None]:
    return {
        "xml_sha256": sha256(xml_path) if xml_path.is_file() else None,
        "image_sha256": sha256(image_path) if image_path.is_file() else None,
    }


def inspect_image(
    voc_root: Path, image_id: str, pixel_origin: str
) -> tuple[dict[str, object], dict[str, object]]:
    """Return the evaluator entry and the selection record of one eligible image.

    Raises ``IneligibleImageError`` with the reason otherwise.
    """
    xml_path = voc_root / "Annotations" / f"{image_id}.xml"
    image_path = voc_root / "JPEGImages" / f"{image_id}.jpg"
    if not xml_path.is_file() or not image_path.is_file():
        raise IneligibleImageError("missing XML or JPEG file")
    try:
        voc = read_voc(xml_path, pixel_origin)
        info = read_image_info(image_path)
    except (ValueError, ET.ParseError) as exc:
        raise IneligibleImageError(f"unreadable file: {exc}") from exc
    if (info["width"], info["height"]) != (voc["width"], voc["height"]):
        raise IneligibleImageError(
            f"XML size {voc['width']}x{voc['height']} differs from the image "
            f"{info['width']}x{info['height']}"
        )
    if info["exif_orientation"] not in (None, 1):
        raise IneligibleImageError(f"EXIF orientation {info['exif_orientation']}")
    try:
        TextDetectionParser("pixel").parse(
            json.dumps(voc["objects"]), voc["width"], voc["height"]
        )
    except ValueError as exc:
        raise IneligibleImageError(f"invalid annotation: {exc}") from exc
    duplicates = find_duplicates(voc["objects"])
    if duplicates:
        raise IneligibleImageError(
            "suspicious duplicate boxes: " + "; ".join(duplicates)
        )

    entry = {
        "image_id": image_id,
        "width": voc["width"],
        "height": voc["height"],
        "objects": voc["objects"],
    }
    record = {
        "image_id": image_id,
        "image": str(image_path),
        "xml": str(xml_path),
        **_hashes(xml_path, image_path),
        "xml_filename": voc["filename"],
        "objects_per_class": dict(Counter(o["cls"] for o in voc["objects"])),
    }
    return entry, record


def select_images(
    voc_root: Path,
    candidates: list[str],
    limit: int,
    pixel_origin: str,
    excluded_ids: dict[str, str] | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    """Select the first ``limit`` eligible candidates; return annotations and record."""
    if limit < 1:
        raise ValueError("The limit must be at least 1.")
    excluded_ids = excluded_ids or {}
    images, records, excluded = [], [], []
    for image_id in candidates:
        if len(images) == limit:
            break
        hashes = _hashes(
            voc_root / "Annotations" / f"{image_id}.xml",
            voc_root / "JPEGImages" / f"{image_id}.jpg",
        )
        if image_id in excluded_ids:
            excluded.append({"image_id": image_id, "reason": excluded_ids[image_id]})
            excluded[-1] |= hashes
            continue
        try:
            entry, record = inspect_image(voc_root, image_id, pixel_origin)
        except IneligibleImageError as exc:
            excluded.append({"image_id": image_id, "reason": str(exc)} | hashes)
            continue
        images.append(entry)
        records.append(record)

    if len(images) < limit:
        raise ValueError(
            f"Only {len(images)} eligible images among {len(candidates)} "
            f"candidates; cannot select {limit}."
        )
    selected = [record["image_id"] for record in records]
    first_window = candidates[:limit]
    replaced = [image_id for image_id in first_window if image_id not in selected]
    replacements = [image_id for image_id in selected if image_id not in first_window]
    selection = {
        "rule": SELECTION_RULE,
        "pixel_origin": pixel_origin,
        "classes": list(CLASSES),
        "duplicate_iou_threshold": DUPLICATE_IOU,
        "candidate_ids": candidates,
        "limit": limit,
        "excluded": excluded,
        "substitutions": [
            {"excluded": old, "replaced_by": new}
            for old, new in zip(replaced, replacements, strict=True)
        ],
        "images": records,
    }
    return {"images": images}, selection


def check_class_names(model_classes: list[str] | tuple[str, ...]) -> None:
    """Require the model to use exactly the annotation class names."""
    if sorted(model_classes) != sorted(CLASSES):
        raise ValueError(
            f"Model classes {list(model_classes)} differ from the annotation "
            f"classes {list(CLASSES)}."
        )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--voc-root", type=Path, required=True)
    parser.add_argument("--image-list", required=True, help="e.g. test.txt")
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--pixel-origin", choices=PIXEL_ORIGINS, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--exclude-ids", type=Path, help="one image ID per line")
    parser.add_argument("--exclude-reason", help="required with --exclude-ids")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if bool(args.exclude_ids) != bool(args.exclude_reason):
        parser.error("--exclude-ids and --exclude-reason must be used together.")
    list_file = args.voc_root / "ImageSets" / "Main" / args.image_list
    try:
        candidates = list_image_ids(list_file)
        excluded_ids = (
            dict.fromkeys(list_image_ids(args.exclude_ids), args.exclude_reason)
            if args.exclude_ids
            else {}
        )
        annotations, selection = select_images(
            args.voc_root, candidates, args.limit, args.pixel_origin, excluded_ids
        )
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    selection = {
        "created_at": datetime.now(UTC).isoformat(),
        "image_list": str(list_file),
        "image_list_sha256": sha256(list_file),
        "exclude_ids_file": str(args.exclude_ids) if args.exclude_ids else None,
        "exclude_ids_sha256": sha256(args.exclude_ids) if args.exclude_ids else None,
    } | selection
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, data in (("annotations", annotations), ("selection", selection)):
        (args.output_dir / f"{name}.json").write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )
    print(
        f"Selected {len(selection['images'])} images "
        f"({len(selection['excluded'])} excluded) into {args.output_dir}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
