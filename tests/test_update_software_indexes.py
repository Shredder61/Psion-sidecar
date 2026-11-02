import copy
import json
import tempfile
import unittest
from pathlib import Path

import update_software_indexes as updater


def program(program_id, name, platforms, *, version="1.0", url="https://example.test/file.zip"):
    return {
        "id": program_id,
        "name": name,
        "versions": [{
            "version": version,
            "variants": [{
                "identifier": "abc123",
                "items": [{
                    "filename": f"{name}.sis",
                    "size": 1234,
                    "reference": [{"name": "package.zip", "url": url}],
                    "kind": "installer",
                    "sha256": "abc123",
                    "id": program_id.rsplit("/", 1)[-1],
                    "name": name,
                }],
            }],
        }],
        "tags": ["epoc32", "installer"],
        "runtimes": ["native"],
        "kinds": ["installer"],
        "platforms": platforms,
        "icon": {"path": "icons/example.gif", "width": 48, "height": 48, "bpp": 2},
    }


class BuildIndexesTests(unittest.TestCase):
    def setUp(self):
        self.catalogue = [
            program("uid/0x1", "Zulu", ["epoc32"], version="2.0"),
            program("sha/abc", "Alpha", ["epoc16"]),
            program("uid/0x2", "Beta", ["epoc32"]),
        ]

    def test_platform_counts_filter_and_sort(self):
        indexes = updater.build_indexes(self.catalogue)
        self.assertEqual(len(indexes["software_index.json"]), 3)
        self.assertEqual([p["name"] for p in indexes["epoc16_index.json"]], ["Alpha"])
        self.assertEqual([p["name"] for p in indexes["epoc32_index.json"]], ["Beta", "Zulu"])
        self.assertEqual(
            set(indexes["epoc16_index.json"][0]),
            set(updater.COMPACT_FIELDS),
        )

    def test_full_catalogue_preserves_download_metadata_exactly(self):
        indexes = updater.build_indexes(self.catalogue)
        self.assertEqual(indexes["software_index.json"], self.catalogue)
        full_by_id = {p["id"]: p for p in indexes["software_index.json"]}
        for filename in ("epoc16_index.json", "epoc32_index.json"):
            for compact in indexes[filename]:
                full = full_by_id[compact["id"]]
                self.assertEqual(compact["name"], full["name"])
                self.assertEqual(compact["platforms"], full["platforms"])
                self.assertIn("versions", full)
                self.assertIn("variants", full["versions"][0])
                self.assertIn("items", full["versions"][0]["variants"][0])
                self.assertIn("reference", full["versions"][0]["variants"][0]["items"][0])
                self.assertIn("url", full["versions"][0]["variants"][0]["items"][0]["reference"][0])

    def test_platform_indexes_do_not_overlap(self):
        indexes = updater.build_indexes(self.catalogue)
        e16 = {p["id"] for p in indexes["epoc16_index.json"]}
        e32 = {p["id"] for p in indexes["epoc32_index.json"]}
        self.assertFalse(e16 & e32)

    def test_rejects_duplicate_ids(self):
        broken = self.catalogue + [copy.deepcopy(self.catalogue[0])]
        with self.assertRaisesRegex(updater.IndexError, "Duplicate program id"):
            updater.build_indexes(broken)

    def test_rejects_missing_required_fields(self):
        broken = copy.deepcopy(self.catalogue)
        del broken[0]["versions"]
        with self.assertRaisesRegex(updater.IndexError, "versions"):
            updater.build_indexes(broken)

    def test_rejects_missing_platform_catalogue(self):
        broken = [p for p in self.catalogue if "epoc16" not in p["platforms"]]
        with self.assertRaisesRegex(updater.IndexError, "epoc16"):
            updater.build_indexes(broken)

    def test_writes_three_valid_json_files(self):
        indexes = updater.build_indexes(self.catalogue)
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir)
            updater.write_indexes(indexes, out)
            for filename, expected in indexes.items():
                with (out / filename).open(encoding="utf-8") as handle:
                    self.assertEqual(json.load(handle), expected)
            self.assertEqual(
                {p.name for p in out.iterdir()},
                {"software_index.json", "epoc16_index.json", "epoc32_index.json"},
            )


if __name__ == "__main__":
    unittest.main()
