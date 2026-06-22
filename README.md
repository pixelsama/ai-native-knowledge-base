# AI-Native Knowledge Base

An open template for a source-grounded knowledge base maintained by coding
agents such as Codex or Claude Code.

The core idea is simple: do not let chat history become knowledge. User
questions are learning signals. Durable knowledge must come from source material,
be converted into canonical Markdown, and then be synthesized into wiki pages,
claims, and interactive learning artifacts.

## Architecture

```text
originals/   uploaded files kept for audit and reconversion
     |
     v
raw/         canonical Markdown source records
     |
     v
wiki/        synthesized knowledge pages
claims/      source-traceable factual claims and conflicts
learning/    interactive HTML explainers, visualizations, quizzes, and labs
questions/   user questions and learning gaps
tasks/       maintenance queues
logs/        ingest, build, decision, and contradiction logs
```

## Why canonical Markdown?

Agents work best when the project has a stable textual substrate. This template
uses Markdown as the canonical source layer:

- local PDFs, Office files, EPUBs, images, audio, and HTML can be converted with
  [Microsoft MarkItDown](https://github.com/microsoft/markitdown);
- web research is written into Markdown under `raw/web/` before synthesis;
- every raw record carries provenance in frontmatter;
- validation can reject source pollution early.

`originals/` may contain the first file you dropped into the system. `raw/`
contains the source record the knowledge base actually consumes.

## Quick Start

Install optional conversion support when you need non-Markdown ingestion:

```bash
python3 -m pip install 'markitdown[all]'
```

Ingest a local Markdown file:

```bash
python3 scripts/ingest.py file originals/pbrt-notes.md \
  --domain computer-graphics \
  --category rendering \
  --title "PBRT Notes" \
  --authority-tier 1
```

Ingest a PDF, DOCX, PPTX, EPUB, or other MarkItDown-supported file:

```bash
python3 scripts/ingest.py file originals/rendering-paper.pdf \
  --domain computer-graphics \
  --category papers \
  --title "Rendering Paper" \
  --authority-tier 1
```

Materialize web research before updating the wiki:

```bash
python3 scripts/ingest.py web \
  --url https://www.khronos.org/vulkan/ \
  --title "Vulkan Overview" \
  --domain computer-graphics \
  --category graphics-api \
  --authority-tier 1 < /tmp/vulkan-overview.md
```

Validate the repository:

```bash
python3 -m unittest discover -s tests
python3 scripts/validate_kb.py
```

## Agent Workflow

1. Treat the user's question as a research signal.
2. Check whether `wiki/` and `claims/` already answer it from existing sources.
3. If the knowledge base is insufficient, ingest authoritative material into
   `raw/` first.
4. Update synthesized pages only after source material exists.
5. Generate interactive learning artifacts under `learning/` when useful.
6. Run validation and commit a reviewable diff.

## Learning Artifacts

Interactive teaching outputs live in `learning/`. Each artifact is a small
package:

```text
learning/computer-graphics/brdf/
  index.html
  manifest.json
  sources.md
  assets/
```

These files are compiled learning interfaces. They may simplify concepts for
pedagogy, but they must disclose approximations and trace back to source records.

## License

MIT.
