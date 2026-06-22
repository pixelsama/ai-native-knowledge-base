#!/usr/bin/env python3
"""Ingest source material into canonical Markdown raw records."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "untitled"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quote(value: object) -> str:
    if isinstance(value, int):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def frontmatter(fields: dict[str, object]) -> str:
    lines = ["---"]
    for key, value in fields.items():
        lines.append(f"{key}: {quote(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def relative_to_root(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


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


def write_raw(output: Path, metadata: dict[str, object], body: str, overwrite: bool = False) -> Path:
    if output.exists() and not overwrite:
        raise FileExistsError(f"{output} already exists; pass --overwrite to replace it")
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized_body = body if body.endswith("\n") else body + "\n"
    output.write_text(frontmatter(metadata) + normalized_body, encoding="utf-8")
    return output


def convert_with_markitdown(input_path: Path) -> tuple[str, str]:
    try:
        from markitdown import MarkItDown
    except ImportError as exc:
        raise RuntimeError(
            "MarkItDown is required for non-Markdown files. Install with: "
            "python3 -m pip install 'markitdown[all]'"
        ) from exc

    result = MarkItDown().convert(str(input_path))
    text = getattr(result, "text_content", None)
    if not text:
        raise RuntimeError(f"MarkItDown returned no text for {input_path}")
    return text, "markitdown"


def ingest_markdown_file(
    *,
    input_path: Path,
    repo_root: Path,
    category: str,
    title: str | None = None,
    source_type: str = "document",
    authority_tier: int = 3,
    overwrite: bool = False,
) -> Path:
    input_path = input_path.resolve()
    repo_root = repo_root.resolve()
    title = title or input_path.stem.replace("-", " ").replace("_", " ").title()

    if input_path.suffix.lower() in {".md", ".markdown"}:
        body = input_path.read_text(encoding="utf-8")
        converter = "direct-markdown"
    else:
        body, converter = convert_with_markitdown(input_path)

    output = repo_root / "raw" / "imported" / slugify(category) / f"{slugify(title)}.md"
    metadata = {
        "title": title,
        "source_type": source_type,
        "source_origin": "uploaded-file",
        "original_file": relative_to_root(input_path, repo_root),
        "converter": converter,
        "converted_at": utc_now(),
        "content_hash": sha256_file(input_path),
        "authority_tier": authority_tier,
        "trust": "source-derived",
        "status": "canonical-raw",
    }
    return write_raw(output, metadata, body, overwrite=overwrite)


def ingest_web_markdown(
    *,
    body: str,
    repo_root: Path,
    url: str,
    title: str,
    category: str,
    source_type: str = "web",
    authority_tier: int = 3,
    overwrite: bool = False,
) -> Path:
    repo_root = repo_root.resolve()
    output = repo_root / "raw" / "web" / slugify(category) / f"{slugify(title)}.md"
    metadata = {
        "title": title,
        "source_type": source_type,
        "source_origin": "web-research",
        "url": url,
        "retrieved_at": utc_now(),
        "authority_tier": authority_tier,
        "trust": "source-derived",
        "status": "canonical-raw",
    }
    return write_raw(output, metadata, body, overwrite=overwrite)


@dataclass
class BatchIngestResult:
    created: list[Path]
    skipped: list[Path]


def existing_raw_hashes(repo_root: Path) -> set[str]:
    hashes: set[str] = set()
    raw_root = repo_root / "raw"
    if not raw_root.exists():
        return hashes
    for path in raw_root.rglob("*.md"):
        if path.name == "README.md":
            continue
        metadata = parse_frontmatter(path)
        if metadata and metadata.get("content_hash"):
            hashes.add(metadata["content_hash"])
    return hashes


def iter_original_files(originals_root: Path) -> Iterable[Path]:
    if not originals_root.exists():
        return []
    return (
        path
        for path in sorted(originals_root.rglob("*"))
        if path.is_file() and not path.name.startswith(".") and path.name != "README.md"
    )


def category_for_original(path: Path, originals_root: Path, fallback: str) -> str:
    rel = path.resolve().relative_to(originals_root.resolve())
    if len(rel.parts) > 1:
        return rel.parts[0]
    return fallback


def target_for_original(repo_root: Path, path: Path, originals_root: Path, fallback_category: str) -> Path:
    category = category_for_original(path, originals_root, fallback_category)
    title = path.stem.replace("-", " ").replace("_", " ").title()
    return repo_root.resolve() / "raw" / "imported" / slugify(category) / f"{slugify(title)}.md"


def ingest_originals(
    *,
    repo_root: Path,
    originals_dir: Path | None = None,
    default_category: str = "uncategorized",
    source_type: str = "document",
    authority_tier: int = 3,
    dry_run: bool = False,
    overwrite: bool = False,
) -> BatchIngestResult:
    repo_root = repo_root.resolve()
    originals_root = (originals_dir or repo_root / "originals").resolve()
    known_hashes = existing_raw_hashes(repo_root)
    created: list[Path] = []
    skipped: list[Path] = []

    for path in iter_original_files(originals_root):
        digest = sha256_file(path)
        if not overwrite and digest in known_hashes:
            skipped.append(path.resolve())
            continue

        target = target_for_original(repo_root, path, originals_root, default_category)
        if dry_run:
            created.append(target)
            continue

        category = category_for_original(path, originals_root, default_category)
        output = ingest_markdown_file(
            input_path=path,
            repo_root=repo_root,
            category=category,
            title=path.stem.replace("-", " ").replace("_", " ").title(),
            source_type=source_type,
            authority_tier=authority_tier,
            overwrite=overwrite,
        )
        known_hashes.add(digest)
        created.append(output)

    return BatchIngestResult(created=created, skipped=skipped)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)

    file_parser = subparsers.add_parser("file", help="Convert or copy a local source into raw/imported/")
    file_parser.add_argument("input_path", type=Path)
    file_parser.add_argument("--category", required=True)
    file_parser.add_argument("--title")
    file_parser.add_argument("--source-type", default="document")
    file_parser.add_argument("--authority-tier", type=int, default=3)
    file_parser.add_argument("--overwrite", action="store_true")

    originals_parser = subparsers.add_parser(
        "originals", help="Batch-convert unprocessed files from originals/ into raw/imported/"
    )
    originals_parser.add_argument("--originals-dir", type=Path)
    originals_parser.add_argument("--default-category", default="uncategorized")
    originals_parser.add_argument("--source-type", default="document")
    originals_parser.add_argument("--authority-tier", type=int, default=3)
    originals_parser.add_argument("--dry-run", action="store_true")
    originals_parser.add_argument("--overwrite", action="store_true")

    web_parser = subparsers.add_parser("web", help="Materialize web research Markdown into raw/web/")
    web_parser.add_argument("--url", required=True)
    web_parser.add_argument("--title", required=True)
    web_parser.add_argument("--category", required=True)
    web_parser.add_argument("--source-type", default="web")
    web_parser.add_argument("--authority-tier", type=int, default=3)
    web_parser.add_argument("--body-file", type=Path, help="Markdown body file; defaults to stdin")
    web_parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "file":
            output = ingest_markdown_file(
                input_path=args.input_path,
                repo_root=args.repo_root,
                category=args.category,
                title=args.title,
                source_type=args.source_type,
                authority_tier=args.authority_tier,
                overwrite=args.overwrite,
            )
        elif args.command == "web":
            body = args.body_file.read_text(encoding="utf-8") if args.body_file else sys.stdin.read()
            output = ingest_web_markdown(
                body=body,
                repo_root=args.repo_root,
                url=args.url,
                title=args.title,
                category=args.category,
                source_type=args.source_type,
                authority_tier=args.authority_tier,
                overwrite=args.overwrite,
            )
        else:
            result = ingest_originals(
                repo_root=args.repo_root,
                originals_dir=args.originals_dir,
                default_category=args.default_category,
                source_type=args.source_type,
                authority_tier=args.authority_tier,
                dry_run=args.dry_run,
                overwrite=args.overwrite,
            )
            for path in result.created:
                print(f"created: {relative_to_root(path, args.repo_root)}")
            for path in result.skipped:
                print(f"skipped: {relative_to_root(path, args.repo_root)}")
            print(f"summary: {len(result.created)} created, {len(result.skipped)} skipped")
            return 0
    except Exception as exc:
        parser.exit(1, f"ingest failed: {exc}\n")

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
