import unittest

from scrabble.rules import (
    BINGO_BONUS,
    DOUBLE_LETTER,
    DOUBLE_WORD,
    LETTER_DISTRIBUTION,
    LETTER_VALUES,
    PREMIUM_SQUARES,
    TRIPLE_LETTER,
    TRIPLE_WORD,
    new_bag,
    score_word,
    validate_tile_distribution,
)


class ScrabbleRulesTests(unittest.TestCase):
    def test_standard_english_bag_has_100_tiles(self):
        self.assertTrue(validate_tile_distribution())
        self.assertEqual(len(new_bag()), 100)
        self.assertEqual(sum(LETTER_DISTRIBUTION.values()), 100)
        self.assertEqual(LETTER_DISTRIBUTION["?"], 2)

    def test_letter_values(self):
        self.assertEqual(LETTER_VALUES["A"], 1)
        self.assertEqual(LETTER_VALUES["D"], 2)
        self.assertEqual(LETTER_VALUES["B"], 3)
        self.assertEqual(LETTER_VALUES["F"], 4)
        self.assertEqual(LETTER_VALUES["K"], 5)
        self.assertEqual(LETTER_VALUES["J"], 8)
        self.assertEqual(LETTER_VALUES["Q"], 10)
        self.assertEqual(LETTER_VALUES["?"], 0)

    def test_premium_square_counts(self):
        self.assertEqual(len(TRIPLE_WORD), 8)
        self.assertEqual(len(DOUBLE_WORD), 17)
        self.assertEqual(len(TRIPLE_LETTER), 12)
        self.assertEqual(len(DOUBLE_LETTER), 24)
        self.assertEqual(len(PREMIUM_SQUARES), 61)

    def test_centre_double_word_applies_to_first_word(self):
        self.assertEqual(
            score_word("CAT", [(7, 6), (7, 7), (7, 8)], {(7, 6), (7, 7), (7, 8)}),
            10,
        )

    def test_premium_only_applies_when_tile_is_new(self):
        # The existing A on a double-letter square is not doubled again.
        self.assertEqual(
            score_word("AT", [(0, 3), (0, 4)], {(0, 4)}),
            2,
        )

    def test_blank_scores_zero_even_on_letter_premium(self):
        self.assertEqual(
            score_word("CAT", [(7, 6), (7, 7), (7, 8)], {(7, 6), (7, 7), (7, 8)}, {(7, 6)}),
            8,
        )

    def test_word_multiplier_applies_to_entire_word(self):
        self.assertEqual(
            score_word("AT", [(0, 0), (0, 1)], {(0, 0), (0, 1)}),
            6,
        )

    def test_length_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            score_word("CAT", [(7, 7)], {(7, 7)})


if __name__ == "__main__":
    unittest.main()
