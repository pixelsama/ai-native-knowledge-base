#!/usr/bin/env python3
"""Validate knowledge-base integrity rules."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.frontmatter import parse_frontmatter
except ModuleNotFoundError:
    from frontmatter import parse_frontmatter


RAW_REQUIRED_FIELDS = {
    "title",
    "source_type",
    "source_origin",
    "authority_tier",
    "trust",
    "status",
    "content_hash",
}


@dataclass
class ValidationResult:
    errors: list[str]
    warnings: list[str]


def should_skip_raw_file(path: Path) -> bool:
    return path.name.startswith(".") or path.name == "README.md"


def iter_markdown_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return (
        path
        for path in sorted(root.rglob("*.md"))
        if path.is_file() and not path.name.startswith(".") and path.name != "README.md"
    )


def parse_authority_tier(value: Any) -> int | None:
    try:
        tier = int(value)
    except (TypeError, ValueError):
        return None
    if tier < 1 or tier > 4:
        return None
    return tier


def validate_raw(repo_root: Path) -> tuple[list[str], dict[str, dict[str, Any]]]:
    errors: list[str] = []
    raw_metadata: dict[str, dict[str, Any]] = {}
    raw_root = repo_root / "raw"
    if not raw_root.exists():
        errors.append("raw/ is missing")
        return errors, raw_metadata

    for path in raw_root.rglob("*"):
        if not path.is_file() or should_skip_raw_file(path):
            continue
        rel = path.relative_to(repo_root).as_posix()
        if path.suffix.lower() not in {".md", ".markdown"}:
            errors.append(f"{rel}: raw/ may contain Markdown files only")
            continue
        metadata = parse_frontmatter(path)
        if metadata is None:
            errors.append(f"{rel}: missing required frontmatter block")
            continue
        raw_metadata[rel] = metadata
        missing = sorted(RAW_REQUIRED_FIELDS - set(metadata))
        if missing:
            errors.append(f"{rel}: missing required frontmatter fields: {', '.join(missing)}")
        if metadata.get("status") != "canonical-raw":
            errors.append(f"{rel}: status must be canonical-raw")
        if parse_authority_tier(metadata.get("authority_tier")) is None:
            errors.append(f"{rel}: authority_tier must be an integer from 1 to 4")
        if metadata.get("source_origin") == "web-research" and "url" not in metadata:
            errors.append(f"{rel}: web-research raw records must include url")
        if metadata.get("source_origin") == "uploaded-file" and "original_file" not in metadata:
            errors.append(f"{rel}: uploaded-file raw records must include original_file")

    return errors, raw_metadata


def validate_sourced_markdown(
    *,
    repo_root: Path,
    section: str,
    raw_metadata: dict[str, dict[str, Any]],
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    section_root = repo_root / section

    for path in iter_markdown_files(section_root):
        rel = path.relative_to(repo_root).as_posix()
        metadata = parse_frontmatter(path)
        if metadata is None:
            errors.append(f"{rel}: missing required frontmatter block")
            continue
        sources = metadata.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append(f"{rel}: sources must be a non-empty YAML list")
            continue

        tiers: list[int] = []
        for source in sources:
            if not isinstance(source, str):
                errors.append(f"{rel}: sources entries must be strings")
                continue
            if source.startswith(("http://", "https://")):
                errors.append(f"{rel}: sources must reference raw/ files, not external URLs: {source}")
                continue
            if not source.startswith("raw/"):
                errors.append(f"{rel}: sources must reference raw/ files: {source}")
                continue
            source_path = repo_root / source
            if not source_path.exists():
                errors.append(f"{rel}: source does not exist: {source}")
                continue
            if not source_path.is_file() or source_path.suffix.lower() not in {".md", ".markdown"}:
                errors.append(f"{rel}: source is not a Markdown raw file: {source}")
                continue
            tier = parse_authority_tier(raw_metadata.get(source, {}).get("authority_tier"))
            if tier is not None:
                tiers.append(tier)

        if sources and tiers and all(tier > 2 for tier in tiers):
            warnings.append(f"{rel}: sources include only low-authority sources (Tier 3 or 4)")

    return ValidationResult(errors=errors, warnings=warnings)


def validate_learning(repo_root: Path) -> list[str]:
    errors: list[str] = []
    learning_root = repo_root / "learning"
    if not learning_root.exists():
        return errors

    for index in learning_root.rglob("index.html"):
        artifact_dir = index.parent
        rel = artifact_dir.relative_to(repo_root).as_posix()
        manifest = artifact_dir / "manifest.json"
        sources = artifact_dir / "sources.md"
        if not manifest.exists():
            errors.append(f"{rel}: interactive learning artifact is missing manifest.json")
        if not sources.exists():
            errors.append(f"{rel}: interactive learning artifact is missing sources.md")
        if manifest.exists():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{rel}/manifest.json: invalid JSON: {exc}")
                continue
            generated_from = data.get("generated_from", [])
            if not isinstance(generated_from, list):
                errors.append(f"{rel}/manifest.json: generated_from must be a list")
                continue
            for source in generated_from:
                if isinstance(source, str) and not source.startswith(("http://", "https://")):
                    if not (repo_root / source).exists():
                        errors.append(f"{rel}/manifest.json: generated_from source does not exist: {source}")
    return errors


def validate_with_warnings(repo_root: Path) -> ValidationResult:
    repo_root = repo_root.resolve()
    raw_errors, raw_metadata = validate_raw(repo_root)
    wiki_result = validate_sourced_markdown(repo_root=repo_root, section="wiki", raw_metadata=raw_metadata)
    claims_result = validate_sourced_markdown(repo_root=repo_root, section="claims", raw_metadata=raw_metadata)
    return ValidationResult(
        errors=raw_errors + wiki_result.errors + claims_result.errors + validate_learning(repo_root),
        warnings=wiki_result.warnings + claims_result.warnings,
    )


def validate(repo_root: Path) -> list[str]:
    return validate_with_warnings(repo_root).errors


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    result = validate_with_warnings(args.repo_root)
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    if result.errors:
        for error in result.errors:
            print(f"ERROR: {error}")
        return 1
    print("Knowledge base validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
