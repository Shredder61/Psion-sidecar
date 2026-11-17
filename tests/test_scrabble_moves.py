import unittest

from scrabble.board import Board, Tile
from scrabble.moves import InvalidMove, evaluate_move


class MoveValidationTests(unittest.TestCase):
    def test_opening_move_must_cover_centre(self):
        board = Board()
        with self.assertRaisesRegex(InvalidMove, "centre"):
            evaluate_move(board, {(7, 6): Tile("C"), (7, 8): Tile("T")})

    def test_opening_move_scores_centre_double_word(self):
        result = evaluate_move(
            Board(),
            {(7, 6): Tile("C"), (7, 7): Tile("A"), (7, 8): Tile("T")},
            {"CAT"},
        )
        self.assertEqual(result.score, 10)
        self.assertEqual([word.letters for word in result.words], ["CAT"])

    def test_move_must_be_in_one_row_or_column(self):
        with self.assertRaisesRegex(InvalidMove, "one row or one column"):
            evaluate_move(
                Board(),
                {(7, 7): Tile("C"), (7, 8): Tile("A"), (8, 8): Tile("T")},
            )

    def test_gap_without_existing_tile_is_rejected(self):
        with self.assertRaisesRegex(InvalidMove, "contiguous"):
            evaluate_move(
                Board(),
                {(7, 6): Tile("C"), (7, 8): Tile("T")},
            )

    def test_existing_tile_can_bridge_a_move(self):
        board = Board()
        board.place_tile((7, 7), Tile("A"))
        result = evaluate_move(
            board,
            {(7, 6): Tile("C"), (7, 8): Tile("T")},
            {"CAT"},
        )
        self.assertEqual(result.score, 5)  # C + existing A + T; no old premium

    def test_subsequent_move_must_connect_to_board(self):
        board = Board()
        board.place_tiles({(7, 7): Tile("C"), (7, 8): Tile("A")})
        with self.assertRaisesRegex(InvalidMove, "connect"):
            evaluate_move(board, {(0, 0): Tile("T"), (0, 1): Tile("O")})

    def test_cross_word_is_scored_as_well_as_main_word(self):
        board = Board()
        board.place_tiles({
            (7, 6): Tile("C"),
            (7, 7): Tile("A"),
            (6, 8): Tile("T"),
        })
        result = evaluate_move(board, {(7, 8): Tile("R")})
        self.assertEqual({word.letters for word in result.words}, {"CAR", "TR"})
        self.assertEqual(result.score, 7)

    def test_dictionary_checks_every_formed_word(self):
        board = Board()
        with self.assertRaisesRegex(InvalidMove, "not in dictionary"):
            evaluate_move(
                board,
                {(7, 7): Tile("C"), (7, 8): Tile("A")},
                {"CAT"},
            )

    def test_callable_dictionary_is_supported(self):
        result = evaluate_move(
            Board(),
            {(7, 7): Tile("C"), (7, 8): Tile("A")},
            lambda word: word == "CA",
        )
        self.assertEqual(result.score, 8)

    def test_blank_scores_zero_when_placed(self):
        result = evaluate_move(
            Board(),
            {(7, 7): Tile("C", True), (7, 8): Tile("A")},
            {"CA"},
        )
        self.assertEqual(result.score, 2)

    def test_bingo_bonus_for_seven_tiles(self):
        board = Board()
        # Seven-letter opening word across the centre.
        placements = {
            (7, column): Tile(letter)
            for column, letter in zip(range(4, 11), "READING")
        }
        result = evaluate_move(board, placements, {"READING"})
        self.assertTrue(result.bingo)
        self.assertEqual(result.score, 50 + 2 * sum(
            Tile(letter).points for letter in "READING"
        ))

    def test_invalid_move_does_not_mutate_board(self):
        board = Board()
        with self.assertRaises(InvalidMove):
            evaluate_move(board, {(7, 7): Tile("C")})
        self.assertTrue(board.is_empty)


if __name__ == "__main__":
    unittest.main()
