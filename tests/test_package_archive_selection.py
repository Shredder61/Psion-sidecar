#!/usr/bin/env python3
"""Regression tests for choosing the correct downloadable package archive."""

import sys
import unittest
from pathlib import Path

# Running this file directly puts tests/ on sys.path, not the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sidecar_web


def ref(name, url):
    return {"name": name, "url": url}


class PackageArchiveSelectionTests(unittest.TestCase):
    def test_selects_archive_whose_name_matches_installer(self):
        expected = ref(
            "s3export.zip",
            "https://downloads.example/s3export.zip",
        )
        references = [
            ref("shared-tools.zip", "https://downloads.example/shared-tools.zip"),
            expected,
        ]

        self.assertEqual(
            sidecar_web._find_package_archive("s3export.app", references),
            expected,
        )

    def test_does_not_select_unrelated_zip(self):
        references = [
            ref("shared-tools.zip", "https://downloads.example/shared-tools.zip"),
            ref("utilities.zip", "https://downloads.example/utilities.zip"),
        ]

        self.assertIsNone(
            sidecar_web._find_package_archive("s3export.app", references)
        )

    def test_prefers_exact_match_over_partial_name_match(self):
        exact = ref("s3export.zip", "https://downloads.example/s3export.zip")
        partial = ref(
            "s3export-collection.zip",
            "https://downloads.example/s3export-collection.zip",
        )

        self.assertEqual(
            sidecar_web._find_package_archive(
                "s3export.app", [partial, exact]
            ),
            exact,
        )

    def test_uses_parent_directory_alias_for_differently_named_package(self):
        installer = ref("banktran/s3export.app", "")
        package = ref("banktran.zip", "https://downloads.example/banktran.zip")

        self.assertEqual(
            sidecar_web._find_package_archive(
                "s3export.app", [installer, package]
            ),
            package,
        )

    def test_ignores_zip_file_nested_inside_non_archive_org_archive(self):
        references = [
            ref(
                "s3export.zip",
                "https://downloads.example/collection.iso/s3export.zip",
            )
        ]

        self.assertIsNone(
            sidecar_web._find_package_archive("s3export.app", references)
        )

    def test_allows_matching_zip_nested_in_archive_org_collection(self):
        expected = ref(
            "s3export.zip",
            "https://archive.org/download/example/collection.iso/s3export.zip",
        )
        references = [
            ref(
                "other.zip",
                "https://downloads.example/other.zip",
            ),
            expected,
        ]

        self.assertEqual(
            sidecar_web._find_package_archive("s3export.app", references),
            expected,
        )

    def test_uses_url_filename_when_reference_name_is_missing(self):
        expected = {"url": "https://downloads.example/s3export.zip"}
        references = [
            {"url": "https://downloads.example/unrelated.zip"},
            expected,
        ]

        self.assertEqual(
            sidecar_web._find_package_archive("s3export.app", references),
            expected,
        )

    def test_returns_none_when_references_are_empty(self):
        self.assertIsNone(
            sidecar_web._find_package_archive("s3export.app", [])
        )


if __name__ == "__main__":
    unittest.main()
