import tempfile
import unittest
from pathlib import Path

from scripts.validate_kb import validate


class ValidateKnowledgeBaseTests(unittest.TestCase):
    def test_raw_rejects_non_markdown_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw" / "imported" / "paper.pdf"
            raw.parent.mkdir(parents=True)
            raw.write_bytes(b"%PDF")

            errors = validate(root)

            self.assertTrue(any("raw/ may contain Markdown files only" in e for e in errors))

    def test_raw_markdown_requires_canonical_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw" / "web" / "graphics" / "missing.md"
            raw.parent.mkdir(parents=True)
            raw.write_text("# Missing metadata\n", encoding="utf-8")

            errors = validate(root)

            self.assertTrue(any("missing required frontmatter" in e for e in errors))

    def test_learning_artifact_requires_manifest_and_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "learning" / "computer-graphics" / "brdf"
            artifact.mkdir(parents=True)
            (artifact / "index.html").write_text("<!doctype html><title>BRDF</title>", encoding="utf-8")

            errors = validate(root)

            self.assertTrue(any("manifest.json" in e for e in errors))
            self.assertTrue(any("sources.md" in e for e in errors))

    def test_valid_minimal_repository_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw" / "web" / "graphics" / "brdf.md"
            raw.parent.mkdir(parents=True)
            raw.write_text(
                "---\n"
                'title: "BRDF"\n'
                'source_type: "web"\n'
                'source_origin: "web-research"\n'
                'url: "https://example.com/brdf"\n'
                'retrieved_at: "2026-06-22T00:00:00Z"\n'
                'authority_tier: 1\n'
                'trust: "source-derived"\n'
                'status: "canonical-raw"\n'
                "---\n\n# BRDF\n",
                encoding="utf-8",
            )
            artifact = root / "learning" / "computer-graphics" / "brdf"
            artifact.mkdir(parents=True)
            (artifact / "index.html").write_text("<!doctype html><title>BRDF</title>", encoding="utf-8")
            (artifact / "sources.md").write_text("# Sources\n\n- raw/web/graphics/brdf.md\n", encoding="utf-8")
            (artifact / "manifest.json").write_text(
                '{"title":"BRDF","generated_from":["raw/web/graphics/brdf.md"],"artifact_type":"interactive-html"}',
                encoding="utf-8",
            )

            self.assertEqual(validate(root), [])


if __name__ == "__main__":
    unittest.main()
