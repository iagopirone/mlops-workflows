"""Validate the structure of the OKF documentation bundle in docs/.

Uses only the standard library. The frontmatter is read line by line and only
the fields checked here are understood; this is not a full YAML parser.

Internal links must be relative (OKF 0.2, section 6.1) so that they also work
on GitHub; they are resolved from the folder of the file that contains them.
"""

import argparse
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

CATEGORIES = {
    "playbooks": ("Playbook", re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.md$")),
    "references": ("Reference", re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.md$")),
    "diagrams": ("Diagram", re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.md$")),
    "adr": ("ADR", re.compile(r"^\d{3}-[a-z0-9]+(-[a-z0-9]+)*\.md$")),
    "plans": ("Plan", re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(-[a-z0-9]+)*\.md$")),
    "reports": (
        "Report",
        re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(-[a-z0-9]+)*\.md$"),
    ),
}
ROOT_FILES = {"index.md", "log.md", "CLAUDE.md", "handoff.md"}
# Root files that must have frontmatter, with their required type.
ROOT_TYPED = {"handoff.md": "Reference"}
STATUSES = {"draft", "stable", "deprecated"}
EVIDENCE = {"verified", "approved", "hypothesis", "proposal"}
INDEX_LINE = re.compile(r"^\* \[[^\]]+\]\(([^)\s]+\.md)\) - \S")
LINK = re.compile(r"\]\(([^)\s]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
LOG_SECTION = re.compile(r"^## (\d{4}-\d{2}-\d{2})\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")


def read_frontmatter(text: str) -> dict[str, str] | None:
    """Return top-level keys and generated.* subkeys as raw strings."""
    lines = text.split("\n")
    if not lines or lines[0] != "---":
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None
    fields: dict[str, str] = {}
    parent = None
    for line in lines[1:end]:
        if not line.strip():
            continue
        if not line.startswith((" ", "-")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
            parent = key.strip()
        elif parent == "generated" and line.startswith("  ") and ":" in line:
            key, _, value = line.strip().partition(":")
            fields[f"generated.{key.strip()}"] = value.strip()
    return fields


def github_slug(heading: str) -> str:
    """Approximate GitHub's anchor for a Markdown heading."""
    text = re.sub(r"`([^`]*)`", r"\1", heading).strip().lower()
    kept = []
    for char in text:
        category = unicodedata.category(char)
        if char in " -_" or category[0] in "LN":
            kept.append(char)
    return "".join(kept).replace(" ", "-")


def anchors(text: str) -> set[str]:
    """Return GitHub-style anchors of headings outside code fences."""
    found: set[str] = set()
    in_fence = False
    for line in text.split("\n"):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        match = None if in_fence else HEADING.match(line)
        if match:
            found.add(github_slug(match.group(1)))
    return found


def strip_code(text: str) -> str:
    """Remove fenced blocks and inline code so examples are not linted as links."""
    kept = []
    in_fence = False
    for line in text.split("\n"):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            kept.append(re.sub(r"`[^`]*`", "", line))
    return "\n".join(kept)


def index_target(root: Path, directory: Path, target: str) -> str:
    """Return an index entry's target as a path relative to the bundle root."""
    resolved = (directory / target).resolve()
    if resolved.is_relative_to(root):
        return resolved.relative_to(root).as_posix()
    return target


def check_metadata(rel: str, fields: dict[str, str], expected_type: str) -> list[str]:
    errors = []
    if fields.get("type") != expected_type:
        errors.append(
            f"{rel}: type must be {expected_type!r}, found {fields.get('type')!r}"
        )
    status = fields.get("status")
    if status is not None and status not in STATUSES:
        errors.append(f"{rel}: invalid status {status!r}")
    by = fields.get("generated.by")
    if by is not None and not by.startswith("human:"):
        errors.append(f"{rel}: generated.by must start with 'human:', found {by!r}")
    at = fields.get("generated.at")
    if at is not None:
        if not (len(at) > 1 and at[0] == at[-1] and at[0] in "\"'"):
            errors.append(f"{rel}: generated.at must be quoted")
        else:
            try:
                parsed = datetime.fromisoformat(at[1:-1])
            except ValueError:
                parsed = None
            if parsed is None or parsed.tzinfo is None:
                errors.append(
                    f"{rel}: generated.at must be ISO 8601 with a timezone, found {at}"
                )
    evidence = fields.get("evidence_basis")
    if evidence is not None:
        if not (evidence.startswith("[") and evidence.endswith("]")):
            errors.append(f"{rel}: evidence_basis must be an inline list")
        else:
            values = [
                value.strip() for value in evidence[1:-1].split(",") if value.strip()
            ]
            invalid = [value for value in values if value not in EVIDENCE]
            if not values or invalid:
                errors.append(f"{rel}: invalid evidence_basis {evidence}")
    return errors


def check_links(
    rel: str, text: str, root: Path, cache: dict[Path, set[str]]
) -> list[str]:
    errors = []
    source = root / rel
    for target in LINK.findall(strip_code(text)):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        path_part, _, anchor = target.partition("#")
        if path_part.startswith("/"):
            errors.append(f"{rel}: internal link must be relative: {target}")
            continue
        file = (source.parent / path_part).resolve() if path_part else source
        if not file.is_relative_to(root):
            errors.append(f"{rel}: link leaves the bundle: {target}")
            continue
        if not file.is_file():
            errors.append(f"{rel}: broken link {target}")
            continue
        if anchor:
            if file not in cache:
                cache[file] = anchors(file.read_text(encoding="utf-8"))
            if anchor not in cache[file]:
                errors.append(f"{rel}: missing anchor {target}")
    return errors


def check_log(root: Path) -> list[str]:
    dates = [
        match.group(1)
        for line in (root / "log.md").read_text(encoding="utf-8").split("\n")
        if (match := LOG_SECTION.match(line))
    ]
    if not dates:
        return ["log.md: no '## YYYY-MM-DD' sections"]
    if dates != sorted(dates, reverse=True) or len(set(dates)) != len(dates):
        return [f"log.md: sections must be unique and newest first: {dates}"]
    return []


def lint(root: Path) -> list[str]:
    """Return every problem found in the bundle at root."""
    root = root.resolve()
    errors: list[str] = []
    cache: dict[Path, set[str]] = {}
    for missing in sorted(ROOT_FILES - {p.name for p in root.iterdir()}):
        errors.append(f"missing root file {missing}")
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and entry.name not in CATEGORIES:
            errors.append(f"unexpected directory {entry.name}/")
        elif entry.is_file() and entry.name not in ROOT_FILES:
            errors.append(f"unexpected root file {entry.name}")

    documents: list[str] = [
        name for name in sorted(ROOT_FILES) if (root / name).is_file()
    ]
    for folder, (doc_type, pattern) in CATEGORIES.items():
        directory = root / folder
        if not directory.is_dir():
            errors.append(f"missing directory {folder}/")
            continue
        if not (directory / "index.md").is_file():
            errors.append(f"{folder}/: missing index.md")
            continue
        listed = set()
        for line in (directory / "index.md").read_text(encoding="utf-8").split("\n"):
            if match := INDEX_LINE.match(line):
                listed.add(index_target(root, directory, match.group(1)))
        for entry in sorted(directory.iterdir()):
            rel = f"{folder}/{entry.name}"
            if entry.is_dir() or entry.suffix != ".md":
                errors.append(f"unexpected entry {rel}")
                continue
            documents.append(rel)
            if entry.name == "index.md":
                continue
            if not pattern.match(entry.name):
                errors.append(f"{rel}: file name does not match the {folder}/ pattern")
            fields = read_frontmatter(entry.read_text(encoding="utf-8"))
            if fields is None:
                errors.append(f"{rel}: missing frontmatter")
            else:
                errors.extend(check_metadata(rel, fields, doc_type))
            if rel not in listed:
                errors.append(f"{rel}: not listed in {folder}/index.md")
        for rel in sorted(listed):
            if not (root / rel).is_file():
                errors.append(f"{folder}/index.md: lists missing file {rel}")
            elif not rel.startswith(f"{folder}/"):
                errors.append(
                    f"{folder}/index.md: lists file from another folder {rel}"
                )

    for name, doc_type in ROOT_TYPED.items():
        if (root / name).is_file():
            fields = read_frontmatter((root / name).read_text(encoding="utf-8"))
            if fields is None:
                errors.append(f"{name}: missing frontmatter")
            else:
                errors.extend(check_metadata(name, fields, doc_type))

    for rel in documents:
        errors.extend(
            check_links(rel, (root / rel).read_text(encoding="utf-8"), root, cache)
        )
    if (root / "log.md").is_file():
        errors.extend(check_log(root))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path("docs"), help="bundle directory"
    )
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        print(f"Bundle directory not found: {args.root}", file=sys.stderr)
        return 2
    errors = lint(args.root.resolve())
    for error in errors:
        print(error)
    print(f"{len(errors)} problem(s) found." if errors else "OK: no problems found.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
