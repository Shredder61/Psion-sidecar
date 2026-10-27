#!/usr/bin/env python3
"""Regression tests for stale links to converted Guardian crosswords."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sidecar_web


class FakeHandler:
    def __init__(self):
        self.status = None
        self.headers = {}
        self.errors = []

    def send_response(self, status):
        self.status = status

    def send_header(self, name, value):
        self.headers[name] = value

    def end_headers(self):
        pass

    def send_error(self, status, message):
        self.errors.append((status, message))


class ConvertedCrosswordLinkTests(unittest.TestCase):
    def test_existing_converted_file_redirects_to_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            converted = root / "Quick_9095_converted.txt"
            converted.write_text("<grid>\\n", encoding="utf-8")
            handler = FakeHandler()

            with patch.object(sidecar_web, "ROOT", root):
                sidecar_web.SidecarHandler.handle_rmr(
                    handler, {"file": [converted.name]}
                )

            self.assertEqual(handler.status, 302)
            self.assertEqual(handler.headers["Location"], "/Quick_9095_converted.txt")
            self.assertFalse(handler.errors)

    def test_missing_converted_file_returns_404_not_400(self):
        with tempfile.TemporaryDirectory() as directory:
            handler = FakeHandler()

            with patch.object(sidecar_web, "ROOT", Path(directory)):
                sidecar_web.SidecarHandler.handle_rmr(
                    handler, {"file": ["Quick_9095_converted.txt"]}
                )

            self.assertEqual(handler.errors, [(404, "Converted crossword not found")])


if __name__ == "__main__":
    unittest.main()
