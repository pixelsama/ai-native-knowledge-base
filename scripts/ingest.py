#!/usr/bin/env python3
"""Ingest source material into canonical Markdown raw records."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
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
        else:
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
    except Exception as exc:
        parser.exit(1, f"ingest failed: {exc}\n")

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
