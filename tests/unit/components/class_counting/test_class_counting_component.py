"""Tests for the class counting component."""

import pytest

from mlops_workflows.artifacts.class_count.class_count_reference import (
    ClassCountReference,
)
from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.artifacts.detection.detection_content import DetectionContent
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.artifacts.text.text_reference import TextReference
from mlops_workflows.components.class_counting.class_counting_component import (
    ClassCountingComponent,
)


def detection(cls: str, conf: float | None = 0.9) -> Detection:
    """Return a detection of the given class."""
    return Detection(cls=cls, conf=conf, box=[0.0, 0.0, 10.0, 10.0])


@pytest.fixture
def blood_detections() -> DetectionContent:
    """Return two RBC, one WBC and one Bacteria detection."""
    return DetectionContent(
        data=[
            detection("RBC"),
            detection("RBC"),
            detection("WBC"),
            detection("Bacteria"),
        ]
    )


@pytest.fixture
def output_reference(tmp_path) -> ClassCountReference:
    """Return the reference where counts are saved."""
    return ClassCountReference(name="counts", location=str(tmp_path / "counts.json"))


def count(classes, detections, output_reference):
    """Run the component on detections and return the saved counts."""
    component = ClassCountingComponent(classes, output_reference)
    result = component.execute(detections)

    assert result == [output_reference]

    return output_reference.materialize().data


def test_generic_mode_counts_every_class(blood_detections, output_reference):
    """Count all classes in order of first appearance."""
    class_count = count(None, blood_detections, output_reference)

    assert class_count.classes is None
    assert class_count.counts == {"RBC": 2, "WBC": 1, "Bacteria": 1}
    assert list(class_count.counts) == ["RBC", "WBC", "Bacteria"]
    assert class_count.total == 4
    assert class_count.excluded == {}
    assert class_count.detection_count == 4


def test_restricted_mode_counts_only_the_domain(blood_detections, output_reference):
    """Count configured classes, with zeros and exclusions."""
    classes = ["RBC", "WBC", "Platelets"]

    class_count = count(classes, blood_detections, output_reference)

    assert class_count.classes == classes
    assert class_count.counts == {"RBC": 2, "WBC": 1, "Platelets": 0}
    assert list(class_count.counts) == classes
    assert class_count.total == 3
    assert class_count.excluded == {"Bacteria": 1}
    assert class_count.detection_count == 4


def test_configured_order_is_kept(blood_detections, output_reference):
    """List counts in the configured order, not in detection order."""
    classes = ["Platelets", "WBC", "RBC"]

    class_count = count(classes, blood_detections, output_reference)

    assert list(class_count.counts) == classes


def test_configured_classes_without_detections_are_zero(output_reference):
    """List every configured class even when nothing was detected."""
    detections = DetectionContent(data=[detection("Bacteria")])

    class_count = count(["RBC", "WBC"], detections, output_reference)

    assert class_count.counts == {"RBC": 0, "WBC": 0}
    assert class_count.total == 0
    assert class_count.excluded == {"Bacteria": 1}


def test_empty_domain_counts_nothing(blood_detections, output_reference):
    """Exclude every detection when the domain is an empty list."""
    class_count = count([], blood_detections, output_reference)

    assert class_count.classes == []
    assert class_count.counts == {}
    assert class_count.total == 0
    assert class_count.excluded == {"RBC": 2, "WBC": 1, "Bacteria": 1}
    assert class_count.detection_count == 4


@pytest.mark.parametrize(
    ("classes", "expected_counts"),
    [(None, {}), ([], {}), (["RBC", "WBC"], {"RBC": 0, "WBC": 0})],
)
def test_no_detections(output_reference, classes, expected_counts):
    """Count zero detections in every mode."""
    class_count = count(classes, DetectionContent(data=[]), output_reference)

    assert class_count.counts == expected_counts
    assert class_count.total == 0
    assert class_count.excluded == {}
    assert class_count.detection_count == 0


def test_same_class_detections_add_up(output_reference):
    """Add up many detections of the same class."""
    detections = DetectionContent(data=[detection("WBC") for _ in range(5)])

    class_count = count(["WBC"], detections, output_reference)

    assert class_count.counts == {"WBC": 5}
    assert class_count.total == 5


def test_confidence_is_not_filtered(output_reference):
    """Count low and missing confidences as received."""
    detections = DetectionContent(
        data=[
            detection("RBC", conf=0.0),
            detection("RBC", conf=0.01),
            detection("RBC", conf=None),
        ]
    )

    class_count = count(None, detections, output_reference)

    assert class_count.counts == {"RBC": 3}


def test_class_names_are_not_normalized(output_reference):
    """Treat case and whitespace variants as different classes."""
    detections = DetectionContent(
        data=[detection("RBC"), detection("rbc"), detection("RBC "), detection("RBC")]
    )

    restricted = count(["RBC"], detections, output_reference)

    assert restricted.counts == {"RBC": 2}
    assert restricted.excluded == {"rbc": 1, "RBC ": 1}

    generic = count(None, detections, output_reference)

    assert generic.counts == {"RBC": 2, "rbc": 1, "RBC ": 1}


def test_detections_are_preserved(blood_detections, output_reference):
    """Leave the received detections unchanged."""
    original = blood_detections.model_copy(deep=True)

    count(["RBC"], blood_detections, output_reference)

    assert blood_detections == original


def test_configured_classes_are_copied(blood_detections, output_reference):
    """Ignore later changes to the list passed to the constructor."""
    classes = ["RBC"]
    component = ClassCountingComponent(classes, output_reference)
    classes.append("WBC")

    component.execute(blood_detections)

    assert output_reference.materialize().data.counts == {"RBC": 2}


@pytest.mark.parametrize("classes", ["RBC", ("RBC",), ["RBC", 1]])
def test_constructor_rejects_invalid_classes(output_reference, classes):
    """Require None or a list of class names."""
    with pytest.raises(TypeError):
        ClassCountingComponent(classes, output_reference)


def test_constructor_rejects_duplicate_classes(output_reference):
    """Reject a domain with repeated classes."""
    with pytest.raises(ValueError):
        ClassCountingComponent(["RBC", "WBC", "RBC"], output_reference)


def test_prepare_returns_detection_content(tmp_path, output_reference):
    """Load the detection artifact as content."""
    detection_reference = DetectionReference(
        name="detections",
        location=str(tmp_path / "detections.json"),
    )
    DetectionContent(data=[detection("RBC")]).dematerialize(detection_reference)

    component = ClassCountingComponent(None, output_reference)
    prepared = component.prepare([detection_reference])

    assert isinstance(prepared, DetectionContent)
    assert prepared.data == [detection("RBC")]


def test_prepare_rejects_invalid_artifacts(tmp_path, output_reference):
    """Require exactly one DetectionReference."""
    detection_reference = DetectionReference(
        name="detections",
        location=str(tmp_path / "detections.json"),
    )
    text_reference = TextReference(name="text", location=str(tmp_path / "text.txt"))
    component = ClassCountingComponent(None, output_reference)

    with pytest.raises(ValueError):
        component.prepare([])

    with pytest.raises(ValueError):
        component.prepare([text_reference])

    with pytest.raises(ValueError):
        component.prepare([detection_reference, detection_reference])


@pytest.mark.parametrize(
    "prepared_data",
    [None, [detection("RBC")], (DetectionContent(data=[]),)],
)
def test_execute_rejects_invalid_data(tmp_path, output_reference, prepared_data):
    """Reject anything but a DetectionContent, without writing output."""
    component = ClassCountingComponent(None, output_reference)

    with pytest.raises(TypeError):
        component.execute(prepared_data)

    assert not (tmp_path / "counts.json").exists()
