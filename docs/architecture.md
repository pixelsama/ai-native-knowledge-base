# Architecture

This project separates source integrity from learning experience for one
domain-specific knowledge base.

## Layers

1. `originals/` keeps uploaded files for audit, rights review, and conversion
   reruns. It is not a knowledge layer.
2. `raw/` stores canonical Markdown source records with provenance frontmatter.
3. `wiki/` stores synthesized topic pages compiled from raw records.
4. `claims/` stores fine-grained factual statements, confidence, and conflicts.
5. `learning/` stores interactive teaching artifacts generated from wiki and raw
   material.
6. `questions/` stores user questions and learning gaps.

## Data Flow

```text
uploaded file -> originals/ -> MarkItDown -> raw/imported/
web research  -> raw/web/
raw records   -> wiki/ + claims/
wiki + raw     -> learning/
questions     -> tasks/ or source-gap discovery
```

The invariant is that durable knowledge flows through `raw/` before synthesis.
The repository root is the domain boundary. Create another repository from this
template when you want another independent direction.
