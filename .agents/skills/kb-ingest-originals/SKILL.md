---
name: kb-ingest-originals
description: Batch ingest unprocessed files from originals/ into canonical Markdown under raw/imported/. Use when the user asks to convert, import, ingest, process, or batch-convert source files dropped into originals/, including PDFs, Office files, EPUBs, HTML, audio, images, or Markdown files.
---

# Ingest Originals

## Overview

Convert source assets from `originals/` into canonical raw Markdown records.
Use the repository script for deterministic behavior instead of rewriting the
ingestion logic in the chat.

## Workflow

1. Confirm the current working directory is the knowledge base root by checking
   that `AGENTS.md`, `originals/`, `raw/`, and `scripts/ingest.py` exist.
2. If the user only wants to preview work, run:

   ```bash
   python3 scripts/ingest.py originals --dry-run
   ```

3. To ingest unprocessed files, run:

   ```bash
   python3 scripts/ingest.py originals
   ```

4. If source files are directly under `originals/`, they are written to
   `raw/imported/uncategorized/`. If they are under a first-level folder such as
   `originals/rendering/`, that folder becomes the raw category.
5. Files already represented in `raw/` by matching `content_hash` are skipped.
6. After ingestion, run:

   ```bash
   python3 scripts/validate_kb.py
   ```

7. Report created and skipped counts, plus any failures. Do not update `wiki/`,
   `claims/`, or `learning/` in the same step unless the user asks for synthesis.

## Options

- Use `--default-category NAME` to change the category for files directly under
  `originals/`.
- Use `--authority-tier N` when the user gives a source trust level.
- Use `--source-type TYPE` for a uniform batch such as `book`, `paper`, or
  `course`.
- Use `--overwrite` only when the user explicitly wants to regenerate existing
  raw records.

## Failure Handling

- If non-Markdown conversion fails because MarkItDown is missing, tell the user
  to install `markitdown[all]` or install it if the environment allows.
- If only some files fail, preserve successful raw records and report the failed
  file paths.
- Never place converted Markdown outside `raw/imported/`.
