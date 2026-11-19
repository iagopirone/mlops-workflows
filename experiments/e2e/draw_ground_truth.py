"""Draw the human annotations of selected images, to check coordinate alignment.

Run from the repository root, in the project environment:

    uv run python -m experiments.e2e.draw_ground_truth \
        --annotations <annotations.json> --images-dir <JPEGImages> \
        --output-dir <dir> [--image-ids ID ...]

The annotations (pixels of the original image, as the evaluator reads them) are
saved as ``<id>-ground-truth.json`` and drawn with the existing
``DetectionVisualizationComponent`` as ``<id>-ground-truth.png``, with ``GT:``
before each class, so they can be compared with the predicted boxes.
"""

import argparse
import sys
from pathlib import Path

from experiments.mirage.evaluate_detections import load_ground_truth
from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.artifacts.detection.detection_content import DetectionContent
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.components.detection_visualization.detection_visualization_component import (
    DetectionVisualizationComponent,
)


def draw(annotations: Path, images_dir: Path, output_dir: Path, image_ids=None):
    """Save and draw the annotations; return the annotated image paths."""
    ground_truth = load_ground_truth(annotations)
    output_dir.mkdir(parents=True, exist_ok=True)
    drawn = []
    for image_id in image_ids or sorted(ground_truth):
        objects = ground_truth[image_id]["objects"]
        reference = DetectionReference(
            name=f"{image_id}-ground-truth",
            location=str(output_dir / f"{image_id}-ground-truth.json"),
        )
        DetectionContent(
            data=[
                Detection(cls=f"GT:{o['cls']}", conf=None, box=o["box"])
                for o in objects
            ]
        ).dematerialize(reference)
        image = ImageReference(
            name=image_id, location=str(images_dir / f"{image_id}.jpg")
        )
        output = ImageReference(
            name=f"{image_id}-ground-truth",
            location=str(output_dir / f"{image_id}-ground-truth.png"),
        )
        component = DetectionVisualizationComponent(output)
        component.execute(component.prepare([image, reference]))
        drawn.append(Path(output.location))
    return drawn


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--images-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--image-ids", nargs="+")
    args = parser.parse_args(argv)
    for path in draw(
        args.annotations, args.images_dir, args.output_dir, args.image_ids
    ):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
