import tempfile
import unittest
from pathlib import Path

from scrabble.dictionary import WordDictionary, normalise_word


class DictionaryTests(unittest.TestCase):
    def test_words_are_normalised_and_deduplicated(self):
        dictionary = WordDictionary(["cat", "DOG", "Cat"])
        self.assertEqual(len(dictionary), 2)
        self.assertIn("CAT", dictionary)
        self.assertIn("dog", dictionary)
        self.assertNotIn("bird", dictionary)

    def test_contains_is_case_insensitive(self):
        dictionary = WordDictionary(["scrabble"])
        self.assertTrue(dictionary.contains("SCRABBLE"))
        self.assertTrue(dictionary.contains("Scrabble"))

    def test_invalid_lookup_returns_false(self):
        dictionary = WordDictionary(["CAT"])
        self.assertFalse(dictionary.contains(""))
        self.assertFalse(dictionary.contains("can't"))
        self.assertFalse(dictionary.contains(None))

    def test_normalise_rejects_non_alphabetic_entries(self):
        for entry in ("", "two words", "can't", "A1"):
            with self.subTest(entry=entry):
                with self.assertRaises(ValueError):
                    normalise_word(entry)

    def test_loads_one_word_per_line_and_ignores_comments(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "words.txt"
            path.write_text("\ufeff# Example list\ncat\nDOG\n\nCat\n", encoding="utf-8")
            dictionary = WordDictionary.from_file(path)
        self.assertEqual(len(dictionary), 2)
        self.assertIn("CAT", dictionary)
        self.assertIn("dog", dictionary)

    def test_invalid_file_entry_reports_line_number(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "words.txt"
            path.write_text("CAT\ncan't\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 2"):
                WordDictionary.from_file(path)

    def test_missing_file_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.txt"
            with self.assertRaises(FileNotFoundError):
                WordDictionary.from_file(path)


if __name__ == "__main__":
    unittest.main()
