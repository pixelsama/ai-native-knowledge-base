# Claude Code Instructions

Follow `AGENTS.md` as the source of truth for this repository.

Claude Code should behave as a knowledge-base maintainer:

- Convert or materialize sources into canonical Markdown under `raw/`.
- Keep user conversations out of the factual knowledge layer.
- Update `wiki/`, `claims/`, and `learning/` only from source-grounded records.
- Run repository validation before finalizing changes.

Useful commands:

```bash
python3 scripts/ingest.py file originals/example.pdf --domain computer-graphics --category rendering --title "Example Source"
python3 scripts/ingest.py web --url https://example.com --title "Example Web Source" --domain computer-graphics --category rendering < /tmp/source.md
python3 scripts/validate_kb.py
```
