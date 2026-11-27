"""Define the example blood-cell pipeline and check that its structure is valid.

The pipeline is only built and validated: nothing is executed, no model is
loaded and no file is read or written. Detection uses a fake detector; the
finalization uses a placeholder because no finalization component exists yet.
"""

import numpy as np

from mlops_workflows.artifacts.class_count.class_count_reference import (
    ClassCountReference,
)
from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.components.class_counting.class_counting_component import (
    ClassCountingComponent,
)
from mlops_workflows.components.detection_visualization.detection_visualization_component import (
    DetectionVisualizationComponent,
)
from mlops_workflows.components.interface import Component
from mlops_workflows.components.object_detection.object_detection_component import (
    ObjectDetectionComponent,
)
from mlops_workflows.components.object_detection.object_detector import ObjectDetector
from mlops_workflows.pipeline.pipeline import Pipeline
from mlops_workflows.pipeline.step import Step


class FakeDetector(ObjectDetector):
    """Stand in for a real model, which is never loaded here."""

    def detect(self, image: np.ndarray) -> list[Detection]:
        return []


def build_example_pipeline(finalization_component: Component) -> Pipeline:
    """Build detection -> (visualization, counting) -> finalization."""
    image = ImageReference(name="sensor_image", location="example/image.jpg")
    detections = DetectionReference(
        name="detections",
        location="example/detections.json",
    )
    annotated = ImageReference(name="annotated_image", location="example/annotated.jpg")
    counts = ClassCountReference(name="class_counts", location="example/counts.json")

    detect = Step(
        step_name="detect",
        component=ObjectDetectionComponent(FakeDetector(), detections),
        input_artifacts=(image,),
        output_artifacts=(detections,),
    )
    visualize = Step(
        step_name="visualize",
        component=DetectionVisualizationComponent(annotated),
        depends_on=("detect",),
        input_artifacts=(image, detections),
        output_artifacts=(annotated,),
    )
    count = Step(
        step_name="count",
        component=ClassCountingComponent(["RBC", "WBC", "Platelets"], counts),
        depends_on=("detect",),
        input_artifacts=(detections,),
        output_artifacts=(counts,),
    )
    finalize = Step(
        step_name="finalize",
        component=finalization_component,
        depends_on=("visualize", "count"),
        input_artifacts=(annotated, counts),
    )

    return Pipeline(
        pipeline_id="blood-cells",
        steps=(detect, visualize, count),
        finalization=finalize,
    )


def test_example_pipeline_is_valid(component):
    """Accept the example pipeline with its finalization."""
    pipeline = build_example_pipeline(component)

    assert pipeline.pipeline_id == "blood-cells"
    assert [step.step_name for step in pipeline.all_steps] == [
        "detect",
        "visualize",
        "count",
        "finalize",
    ]


def test_finalization_waits_for_the_final_outputs(component):
    """Make the finalization depend on the steps that produce final outputs."""
    pipeline = build_example_pipeline(component)
    steps = {step.step_name: step for step in pipeline.all_steps}

    assert pipeline.finalization.depends_on == ("visualize", "count")
    assert pipeline.finalization.input_artifacts == (
        steps["visualize"].output_artifacts + steps["count"].output_artifacts
    )
