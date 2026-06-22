# AI-Native Knowledge Base Agent Rules

This repository is a source-grounded knowledge base, not a personal memory dump.
Treat it like a maintained software project: every durable knowledge claim needs
source material, provenance, validation, and a reviewable diff.

## Protected Requirements

- User conversations are learning signals, not authoritative sources.
- The knowledge base consumes canonical Markdown under `raw/`.
- Uploaded files must be converted to Markdown before they influence `wiki/`,
  `claims/`, or `learning/`.
- Web research must be materialized as Markdown under `raw/web/` before it is
  synthesized into the knowledge layer.
- Interactive learning artifacts must record their source inputs.

## Directory Contract

- `originals/`: local uploaded assets such as PDF, DOCX, PPTX, EPUB, images, or
  audio. These are not the canonical source layer and are ignored by default.
- `raw/`: canonical Markdown source records. This is the only source layer the
  rest of the knowledge base should consume.
- `wiki/`: synthesized topic pages compiled from `raw/`.
- `claims/`: source-traceable factual claims, conflicts, and confidence notes.
- `questions/`: user questions, learning gaps, and research prompts.
- `learning/`: interactive HTML explainers, quizzes, visualizations, and labs.
- `tasks/`: maintenance tasks, ingestion queues, and synthesis requests.
- `logs/`: ingest logs, build logs, contradiction logs, and decision logs.
- `templates/`: reusable source, wiki, claim, and learning artifact templates.
- `scripts/`: validation and ingestion utilities.

## Ingestion Rules

- Use `scripts/ingest.py file` for local files.
- Use MarkItDown for non-Markdown inputs when available.
- Preserve original file provenance in raw frontmatter.
- Do not place binary files, PDFs, Office files, images, or audio under `raw/`.
- Do not edit `originals/` unless the user explicitly asks.
- Do not summarize web pages straight into `wiki/`. First create a raw Markdown
  record under `raw/web/` with `url`, `retrieved_at`, and source metadata.

## Source Authority Tiers

- Tier 1: papers, textbooks, official standards, official documentation,
  course notes from recognized institutions, and primary author material.
- Tier 2: high-quality engineering blogs, conference talks, vendor technical
  articles, and maintained project documentation.
- Tier 3: tutorials, personal blogs, curated notes, and community references.
- Tier 4: forums, social media, comments, and unsourced summaries. Use these as
  leads only, not durable evidence.

## User Conversation Firewall

- Never promote a user statement into `wiki/` or `claims/` as fact unless it is
  independently verified against authoritative sources.
- Store user input only as a question, hypothesis, learning preference, or task.
- If the user asks a question that the current knowledge base cannot answer,
  identify the gap, find authoritative sources, ingest them into `raw/`, then
  update the synthesized layer.

## Wiki Rules

- Every factual topic page should cite one or more raw records.
- Prefer updating existing topic pages over creating near-duplicates.
- When sources conflict, record the conflict in `logs/contradiction-log.md` or a
  dedicated claim file instead of silently choosing one.
- Mark speculative, pedagogical, or simplified explanations clearly.

## Learning Artifact Rules

- A learning artifact is a compiled teaching interface, not a source.
- Each artifact directory with `index.html` must include `manifest.json` and
  `sources.md`.
- Visualizations may be approximate, but they must label approximations.
- Generated HTML should be standalone unless a manifest declares external
  dependencies.

## Verification

Run these before committing changes:

```bash
python3 -m unittest discover -s tests
python3 scripts/validate_kb.py
```
