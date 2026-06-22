import tempfile
import unittest
from pathlib import Path

from scripts.validate_kb import validate, validate_with_warnings


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
            artifact = root / "learning" / "brdf"
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
                'content_hash: "abc123"\n'
                'authority_tier: 1\n'
                'trust: "source-derived"\n'
                'status: "canonical-raw"\n'
                "---\n\n# BRDF\n",
                encoding="utf-8",
            )
            artifact = root / "learning" / "brdf"
            artifact.mkdir(parents=True)
            (artifact / "index.html").write_text("<!doctype html><title>BRDF</title>", encoding="utf-8")
            (artifact / "sources.md").write_text("# Sources\n\n- raw/web/graphics/brdf.md\n", encoding="utf-8")
            (artifact / "manifest.json").write_text(
                '{"title":"BRDF","generated_from":["raw/web/graphics/brdf.md"],"artifact_type":"interactive-html"}',
                encoding="utf-8",
            )

            self.assertEqual(validate(root), [])

    def test_wiki_sources_must_point_to_existing_raw_files(self):
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
                'content_hash: "abc123"\n'
                'authority_tier: 1\n'
                'trust: "source-derived"\n'
                'status: "canonical-raw"\n'
                "---\n\n# BRDF\n",
                encoding="utf-8",
            )
            wiki = root / "wiki" / "rendering" / "brdf.md"
            wiki.parent.mkdir(parents=True)
            wiki.write_text(
                "---\n"
                'title: "BRDF"\n'
                'status: "draft"\n'
                "sources:\n"
                '  - "raw/web/graphics/missing.md"\n'
                "---\n\n# BRDF\n",
                encoding="utf-8",
            )

            errors = validate(root)

            self.assertTrue(any("source does not exist" in e for e in errors))

    def test_claim_sources_are_read_as_yaml_lists_and_validated(self):
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
                'content_hash: "abc123"\n'
                'authority_tier: 1\n'
                'trust: "source-derived"\n'
                'status: "canonical-raw"\n'
                "---\n\n# BRDF\n",
                encoding="utf-8",
            )
            claim = root / "claims" / "brdf.md"
            claim.parent.mkdir(parents=True)
            claim.write_text(
                "---\n"
                'claim: "BRDFs describe reflectance."\n'
                'status: "draft"\n'
                'confidence: "medium"\n'
                "sources:\n"
                '  - "raw/web/graphics/brdf.md"\n'
                "---\n\n# Claim\n",
                encoding="utf-8",
            )

            self.assertEqual(validate(root), [])

    def test_low_authority_wiki_sources_emit_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw" / "web" / "forum" / "thread.md"
            raw.parent.mkdir(parents=True)
            raw.write_text(
                "---\n"
                'title: "Forum Thread"\n'
                'source_type: "web"\n'
                'source_origin: "web-research"\n'
                'url: "https://example.com/thread"\n'
                'retrieved_at: "2026-06-22T00:00:00Z"\n'
                'content_hash: "abc123"\n'
                'authority_tier: 4\n'
                'trust: "source-derived"\n'
                'status: "canonical-raw"\n'
                "---\n\n# Thread\n",
                encoding="utf-8",
            )
            wiki = root / "wiki" / "rendering" / "brdf.md"
            wiki.parent.mkdir(parents=True)
            wiki.write_text(
                "---\n"
                'title: "BRDF"\n'
                'status: "draft"\n'
                "sources:\n"
                '  - "raw/web/forum/thread.md"\n'
                "---\n\n# BRDF\n",
                encoding="utf-8",
            )

            result = validate_with_warnings(root)

            self.assertEqual(result.errors, [])
            self.assertTrue(any("only low-authority sources" in w for w in result.warnings))


if __name__ == "__main__":
    unittest.main()
