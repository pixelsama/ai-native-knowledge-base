#!/usr/bin/env python3
"""Validate knowledge-base integrity rules."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


RAW_REQUIRED_FIELDS = {
    "title",
    "source_type",
    "source_origin",
    "authority_tier",
    "trust",
    "status",
}


def parse_frontmatter(path: Path) -> dict[str, str] | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    metadata: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')
    return metadata


def should_skip_raw_file(path: Path) -> bool:
    return path.name.startswith(".") or path.name == "README.md"


def validate_raw(repo_root: Path) -> list[str]:
    errors: list[str] = []
    raw_root = repo_root / "raw"
    if not raw_root.exists():
        errors.append("raw/ is missing")
        return errors

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
        missing = sorted(RAW_REQUIRED_FIELDS - set(metadata))
        if missing:
            errors.append(f"{rel}: missing required frontmatter fields: {', '.join(missing)}")
        if metadata.get("status") != "canonical-raw":
            errors.append(f"{rel}: status must be canonical-raw")
        if metadata.get("source_origin") == "web-research" and "url" not in metadata:
            errors.append(f"{rel}: web-research raw records must include url")
        if metadata.get("source_origin") == "uploaded-file" and "original_file" not in metadata:
            errors.append(f"{rel}: uploaded-file raw records must include original_file")

    return errors


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


def validate(repo_root: Path) -> list[str]:
    repo_root = repo_root.resolve()
    return validate_raw(repo_root) + validate_learning(repo_root)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    errors = validate(args.repo_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Knowledge base validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
