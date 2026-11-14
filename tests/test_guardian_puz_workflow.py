import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import guardian_to_puz
import guardian_pi
import sidecar_web


ROOT = Path(__file__).resolve().parent


class GuardianPuzWorkflowTests(unittest.TestCase):
    def test_in_memory_source_conversion_creates_only_puz(self):
        source = (ROOT / "fixtures" / "Quick_17637_guardian.txt").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "Quick_17637.puz"
            puzzle = guardian_to_puz.convert_source(
                source, output, title="Guardian Quick 17637"
            )
            data = output.read_bytes()
            self.assertEqual(data[2:14], b"ACROSS&DOWN" + bytes([0]))
            self.assertEqual(puzzle["width"], 13)
            self.assertEqual(puzzle["height"], 13)
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()),
                             ["Quick_17637.puz"])

    def test_downloader_skips_existing_puz_without_fetching(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "Quick_17637.puz"
            output.write_bytes(b"existing")
            original = guardian_pi.fetch_source
            try:
                guardian_pi.fetch_source = lambda *_: self.fail("must not fetch")
                self.assertTrue(guardian_pi.download_one("quick", 17637, directory))
            finally:
                guardian_pi.fetch_source = original
            self.assertEqual(output.read_bytes(), b"existing")

    def test_rmr_route_and_converter_are_absent(self):
        source = (ROOT.parent / "sidecar_web.py").read_text(encoding="utf-8")
        self.assertNotIn('elif path == "/rmr"', source)
        self.assertNotIn("def handle_rmr", source)
        self.assertNotIn("def send_rmr_download", source)
        self.assertNotIn("crossword_converter", source)

    def test_archive_globs_only_puz_files(self):
        source = (ROOT.parent / "sidecar_web.py").read_text(encoding="utf-8")
        self.assertIn('ROOT.glob("Quick_*.puz")', source)
        self.assertIn('ROOT.glob("Cryptic_*.puz")', source)
        self.assertNotIn('_converted.txt', source)
        self.assertNotIn('"/rmr?', source)

    def test_archive_is_displayed_in_numeric_descending_order(self):
        class FakeHandler:
            def __init__(self):
                self.wfile = io.BytesIO()
                self.status = None
                self.headers = {}

            def send_response(self, status):
                self.status = status

            def send_header(self, name, value):
                self.headers[name] = value

            def end_headers(self):
                pass

        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory)
            for filename in (
                "Quick_99.puz", "Quick_100.puz", "Quick_9.puz",
                "Cryptic_99.puz", "Cryptic_100.puz", "Cryptic_9.puz",
            ):
                (archive / filename).write_bytes(b"puz")

            handler = FakeHandler()
            with patch.object(sidecar_web, "ROOT", archive), \
                    patch.object(guardian_pi, "get_latest_number", return_value=None):
                sidecar_web.SidecarHandler.send_guardian_crossword(handler)

            page = handler.wfile.getvalue().decode("utf-8")
            quick_order = [
                page.index('Quick_100.puz'),
                page.index('Quick_99.puz'),
                page.index('Quick_9.puz'),
            ]
            cryptic_order = [
                page.index('Cryptic_100.puz'),
                page.index('Cryptic_99.puz'),
                page.index('Cryptic_9.puz'),
            ]
            self.assertEqual(quick_order, sorted(quick_order))
            self.assertEqual(cryptic_order, sorted(cryptic_order))
            self.assertEqual(handler.status, 200)


if __name__ == "__main__":
    unittest.main()
