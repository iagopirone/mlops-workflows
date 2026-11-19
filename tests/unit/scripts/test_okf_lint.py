import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "okf_lint.py"
spec = importlib.util.spec_from_file_location("okf_lint", SCRIPT)
okf_lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(okf_lint)

FRONTMATTER = """---
type: {type}
title: Example
description: Example document.
status: draft
generated:
  by: human:someone
  at: "2026-11-18T09:00:00-03:00"
evidence_basis: [verified]
---

# Example

## Section with `code` and accents: decisão
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    write(
        tmp_path / "index.md", "# Index\n\n* [Ref](references/example.md) - example\n"
    )
    write(
        tmp_path / "log.md", "# Log\n\n## 2026-11-18\n\n- b\n\n## 2026-11-17\n\n- a\n"
    )
    write(tmp_path / "CLAUDE.md", "See [index](index.md).\n")
    write(tmp_path / "handoff.md", FRONTMATTER.format(type="Reference"))
    for folder, (doc_type, _) in okf_lint.CATEGORIES.items():
        name = {"adr": "001-example.md", "plans": "2026-11-18-plan-example.md"}.get(
            folder, "2026-11-18-example.md" if folder == "reports" else "example.md"
        )
        write(tmp_path / folder / name, FRONTMATTER.format(type=doc_type))
        write(tmp_path / folder / "index.md", f"* [Example]({name}) - example\n")
    return tmp_path


def test_valid_bundle_has_no_problems(bundle: Path) -> None:
    assert okf_lint.lint(bundle) == []


def test_main_returns_zero_for_valid_bundle(bundle: Path) -> None:
    assert okf_lint.main(["--root", str(bundle)]) == 0


def test_main_returns_one_for_invalid_bundle(bundle: Path) -> None:
    (bundle / "references" / "index.md").write_text("", encoding="utf-8")

    assert okf_lint.main(["--root", str(bundle)]) == 1


def test_main_returns_two_for_missing_root(tmp_path: Path) -> None:
    assert okf_lint.main(["--root", str(tmp_path / "missing")]) == 2


def test_unexpected_root_file_and_directory(bundle: Path) -> None:
    write(bundle / "notes.md", "x")
    (bundle / "misc").mkdir()

    errors = okf_lint.lint(bundle)

    assert "unexpected root file notes.md" in errors
    assert "unexpected directory misc/" in errors


def test_missing_root_file(bundle: Path) -> None:
    (bundle / "handoff.md").unlink()

    assert "missing root file handoff.md" in okf_lint.lint(bundle)


def test_subdirectory_inside_category(bundle: Path) -> None:
    (bundle / "references" / "nested").mkdir()

    assert "unexpected entry references/nested" in okf_lint.lint(bundle)


@pytest.mark.parametrize(
    ("folder", "name"),
    [("adr", "1-example.md"), ("plans", "example.md"), ("references", "Example.md")],
)
def test_file_name_pattern(bundle: Path, folder: str, name: str) -> None:
    doc_type = okf_lint.CATEGORIES[folder][0]
    write(bundle / folder / name, FRONTMATTER.format(type=doc_type))
    with (bundle / folder / "index.md").open("a", encoding="utf-8") as index:
        index.write(f"* [X]({name}) - x\n")

    errors = okf_lint.lint(bundle)

    assert f"{folder}/{name}: file name does not match the {folder}/ pattern" in errors


def test_missing_frontmatter(bundle: Path) -> None:
    write(bundle / "references" / "example.md", "# No frontmatter\n")

    assert "references/example.md: missing frontmatter" in okf_lint.lint(bundle)


def test_type_must_match_folder(bundle: Path) -> None:
    write(bundle / "references" / "example.md", FRONTMATTER.format(type="Playbook"))

    errors = okf_lint.lint(bundle)

    assert any(
        "references/example.md: type must be 'Reference'" in error for error in errors
    )


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("status: draft", "status: final", "invalid status"),
        (
            "by: human:someone",
            "by: openai/gpt-6",
            "generated.by must start with 'human:'",
        ),
        (
            'at: "2026-11-18T09:00:00-03:00"',
            "at: 2026-11-18T09:00:00-03:00",
            "must be quoted",
        ),
        (
            'at: "2026-11-18T09:00:00-03:00"',
            'at: "2026-11-18T09:00:00"',
            "with a timezone",
        ),
        ('at: "2026-11-18T09:00:00-03:00"', 'at: "yesterday"', "with a timezone"),
        ("evidence_basis: [verified]", "evidence_basis: verified", "inline list"),
        (
            "evidence_basis: [verified]",
            "evidence_basis: [guess]",
            "invalid evidence_basis",
        ),
        ("evidence_basis: [verified]", "evidence_basis: []", "invalid evidence_basis"),
    ],
)
def test_invalid_metadata(bundle: Path, old: str, new: str, message: str) -> None:
    text = FRONTMATTER.format(type="Reference").replace(old, new)
    write(bundle / "references" / "example.md", text)

    errors = okf_lint.lint(bundle)

    assert any(
        error.startswith("references/example.md") and message in error
        for error in errors
    )


def test_handoff_metadata_is_checked(bundle: Path) -> None:
    write(bundle / "handoff.md", FRONTMATTER.format(type="Handoff"))

    assert any(error.startswith("handoff.md: type") for error in okf_lint.lint(bundle))


def test_document_missing_from_index(bundle: Path) -> None:
    write(bundle / "references" / "other.md", FRONTMATTER.format(type="Reference"))

    assert "references/other.md: not listed in references/index.md" in okf_lint.lint(
        bundle
    )


def test_index_lists_missing_file(bundle: Path) -> None:
    with (bundle / "references" / "index.md").open("a", encoding="utf-8") as index:
        index.write("* [Gone](gone.md) - gone\n")

    assert (
        "references/index.md: lists missing file references/gone.md"
        in okf_lint.lint(bundle)
    )


def test_broken_relative_link(bundle: Path) -> None:
    write(bundle / "log.md", "## 2026-11-18\n\nSee [x](references/missing.md).\n")

    assert "log.md: broken link references/missing.md" in okf_lint.lint(bundle)


def test_relative_link_is_resolved_from_the_source_folder(bundle: Path) -> None:
    with (bundle / "adr" / "001-example.md").open("a", encoding="utf-8") as doc:
        doc.write("\nSee [ref](../references/example.md) and [log](../log.md).\n")

    assert okf_lint.lint(bundle) == []


def test_absolute_link_rejected(bundle: Path) -> None:
    write(bundle / "log.md", "## 2026-11-18\n\nSee [x](/references/example.md).\n")

    errors = okf_lint.lint(bundle)

    assert "log.md: internal link must be relative: /references/example.md" in errors


def test_link_leaving_the_bundle_rejected(bundle: Path) -> None:
    write(bundle.parent / "outside.md", "x")
    write(bundle / "log.md", "## 2026-11-18\n\nSee [x](../outside.md).\n")

    assert "log.md: link leaves the bundle: ../outside.md" in okf_lint.lint(bundle)


def test_index_lists_file_from_another_folder(bundle: Path) -> None:
    with (bundle / "plans" / "index.md").open("a", encoding="utf-8") as index:
        index.write("* [Ref](../references/example.md) - ref\n")

    errors = okf_lint.lint(bundle)

    assert "plans/index.md: lists file from another folder references/example.md" in (
        errors
    )


def test_anchor_matches_github_slug(bundle: Path) -> None:
    link = "references/example.md#section-with-code-and-accents-decisão"
    write(bundle / "log.md", f"## 2026-11-18\n\n[ok]({link})\n")

    assert okf_lint.lint(bundle) == []


def test_same_file_anchor(bundle: Path) -> None:
    write(bundle / "log.md", "## 2026-11-18\n\n[top](#2026-11-18) [bad](#nope)\n")

    assert okf_lint.lint(bundle) == ["log.md: missing anchor #nope"]


def test_missing_anchor(bundle: Path) -> None:
    write(bundle / "log.md", "## 2026-11-18\n\n[x](references/example.md#nope)\n")

    assert "log.md: missing anchor references/example.md#nope" in okf_lint.lint(bundle)


def test_links_inside_code_are_ignored(bundle: Path) -> None:
    text = "## 2026-11-18\n\n`[x](/missing.md)`\n\n```text\n[y](/missing.md)\n```\n"
    write(bundle / "log.md", text)

    assert okf_lint.lint(bundle) == []


def test_log_sections_must_be_newest_first(bundle: Path) -> None:
    write(bundle / "log.md", "## 2026-11-17\n\n## 2026-11-18\n")

    assert any(error.startswith("log.md: sections") for error in okf_lint.lint(bundle))


def test_log_without_sections(bundle: Path) -> None:
    write(bundle / "log.md", "# Log\n")

    assert "log.md: no '## YYYY-MM-DD' sections" in okf_lint.lint(bundle)


def test_real_docs_bundle_is_valid() -> None:
    assert okf_lint.lint(SCRIPT.parents[1] / "docs") == []
