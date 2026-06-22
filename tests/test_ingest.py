import tempfile
import unittest
from pathlib import Path

from scripts.ingest import ingest_originals, ingest_markdown_file, ingest_web_markdown, slugify


class IngestTests(unittest.TestCase):
    def test_slugify_keeps_stable_ascii_slugs(self):
        self.assertEqual(slugify("BRDF: Energy Conservation!"), "brdf-energy-conservation")

    def test_markdown_file_ingest_writes_canonical_raw_with_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "originals" / "brdf-notes.md"
            source.parent.mkdir()
            source.write_text("# BRDF\n\nA source-derived note.\n", encoding="utf-8")

            output = ingest_markdown_file(
                input_path=source,
                repo_root=root,
                category="rendering",
                title="BRDF Notes",
                source_type="notes",
                authority_tier=2,
            )

            text = output.read_text(encoding="utf-8")
            self.assertEqual(
                output.relative_to(root.resolve()).as_posix(),
                "raw/imported/rendering/brdf-notes.md",
            )
            self.assertIn('source_origin: "uploaded-file"', text)
            self.assertIn('status: "canonical-raw"', text)
            self.assertIn('original_file: "originals/brdf-notes.md"', text)
            self.assertIn("# BRDF", text)

    def test_web_ingest_materializes_research_as_raw_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = ingest_web_markdown(
                body="# Vulkan Ray Tracing\n\nCollected from an authoritative page.",
                repo_root=root,
                url="https://www.khronos.org/vulkan/",
                title="Vulkan Ray Tracing",
                category="graphics-api",
                authority_tier=1,
            )

            text = output.read_text(encoding="utf-8")
            self.assertEqual(
                output.relative_to(root.resolve()).as_posix(),
                "raw/web/graphics-api/vulkan-ray-tracing.md",
            )
            self.assertIn('source_origin: "web-research"', text)
            self.assertIn('url: "https://www.khronos.org/vulkan/"', text)
            self.assertIn('content_hash:', text)
            self.assertIn("# Vulkan Ray Tracing", text)

    def test_originals_batch_ingests_unconverted_files_by_category_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "originals" / "rendering" / "brdf-notes.md"
            source.parent.mkdir(parents=True)
            source.write_text("# BRDF\n\nA source-derived note.\n", encoding="utf-8")

            result = ingest_originals(repo_root=root)

            self.assertEqual([p.relative_to(root.resolve()).as_posix() for p in result.created], [
                "raw/imported/rendering/brdf-notes.md"
            ])
            self.assertEqual(result.skipped, [])
            self.assertTrue((root / "raw" / "imported" / "rendering" / "brdf-notes.md").exists())

    def test_originals_batch_skips_files_with_existing_content_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "originals" / "rendering" / "brdf-notes.md"
            source.parent.mkdir(parents=True)
            source.write_text("# BRDF\n\nA source-derived note.\n", encoding="utf-8")

            first = ingest_originals(repo_root=root)
            second = ingest_originals(repo_root=root)

            self.assertEqual(len(first.created), 1)
            self.assertEqual(second.created, [])
            self.assertEqual(second.skipped, [source.resolve()])

    def test_originals_batch_dry_run_does_not_write_raw_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "originals" / "loose-note.md"
            source.parent.mkdir(parents=True)
            source.write_text("# Loose\n", encoding="utf-8")

            result = ingest_originals(repo_root=root, dry_run=True)

            self.assertEqual([p.relative_to(root.resolve()).as_posix() for p in result.created], [
                "raw/imported/uncategorized/loose-note.md"
            ])
            self.assertFalse((root / "raw").exists())


if __name__ == "__main__":
    unittest.main()
