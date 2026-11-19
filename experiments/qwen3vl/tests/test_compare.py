"""Test the read-only comparison helpers with synthetic answers."""

from experiments.qwen3vl.compare import describe_answer, near_duplicate_pairs, raw_boxes

BROKEN = (
    '```json\n[{"bbox_2d": [1, 2, 3, 4], "label": "red blood cell"},\n'
    '{"bbox_2d": [1, 2, 3, 4], "label": "red blood cell"},\n'
    '{"bbox_2d": [5, 6, 7, 8], "label": "white blood cell"},\n'
    '{"bbox_2d": 355, 0'
)


def test_raw_boxes_ignore_malformed_items():
    assert raw_boxes(BROKEN) == [(1, 2, 3, 4), (1, 2, 3, 4), (5, 6, 7, 8)]


def test_describe_answer_counts_duplicates_and_labels():
    described = describe_answer(BROKEN)

    assert described["raw_boxes"] == 3
    assert described["unique_boxes"] == 2
    assert described["duplicate_boxes"] == 1
    assert described["max_repeats_of_one_box"] == 2
    assert described["raw_labels"] == {"red blood cell": 2, "white blood cell": 1}


def test_describe_text_without_boxes():
    described = describe_answer("A blood smear.")

    assert described["raw_boxes"] == 0
    assert described["max_repeats_of_one_box"] == 0
    assert described["raw_labels"] == {}


def test_near_duplicates_need_same_label_and_overlap():
    answer = (
        '[{"bbox_2d": [0, 0, 10, 10], "label": "a"},'
        ' {"bbox_2d": [1, 0, 11, 10], "label": "a"},'
        ' {"bbox_2d": [1, 0, 11, 10], "label": "b"},'
        ' {"bbox_2d": [50, 50, 60, 60], "label": "a"},'
        ' {"bbox_2d": [0, 0, 10, 10], "label": "a"}]'
    )

    # a/a overlap (IoU 0.82) twice; exact repeats and other labels do not count.
    assert near_duplicate_pairs(answer) == 2
