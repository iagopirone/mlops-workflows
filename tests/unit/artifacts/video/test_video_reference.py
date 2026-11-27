"""Test VideoReference serialization."""

from mlops_workflows.artifacts.video.video_reference import VideoReference


def test_reference_json_contains_only_reference_fields():
    """Serialize and reconstruct a reference without video content."""
    reference = VideoReference(name="video", location="input.avi")

    message = reference.model_dump_json()
    recovered = VideoReference.model_validate_json(message)

    assert reference.model_dump() == {
        "name": "video",
        "location": "input.avi",
    }
    assert recovered == reference
    assert recovered is not reference
