import tempfile
import unittest
from pathlib import Path

from scripts.ingest import ingest_markdown_file, ingest_web_markdown, slugify


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
                domain="computer-graphics",
                category="rendering",
                title="BRDF Notes",
                source_type="notes",
                authority_tier=2,
            )

            text = output.read_text(encoding="utf-8")
            self.assertEqual(
                output.relative_to(root.resolve()).as_posix(),
                "raw/imported/computer-graphics/rendering/brdf-notes.md",
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
                domain="computer-graphics",
                category="graphics-api",
                authority_tier=1,
            )

            text = output.read_text(encoding="utf-8")
            self.assertEqual(
                output.relative_to(root.resolve()).as_posix(),
                "raw/web/computer-graphics/graphics-api/vulkan-ray-tracing.md",
            )
            self.assertIn('source_origin: "web-research"', text)
            self.assertIn('url: "https://www.khronos.org/vulkan/"', text)
            self.assertIn("# Vulkan Ray Tracing", text)


if __name__ == "__main__":
    unittest.main()
