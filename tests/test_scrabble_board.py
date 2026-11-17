import unittest

from scrabble.board import Board, Tile
from scrabble.rules import BOARD_SIZE


class BoardTests(unittest.TestCase):
    def test_new_board_is_empty_and_15_by_15(self):
        board = Board()
        self.assertTrue(board.is_empty)
        self.assertEqual(board.occupied_count, 0)
        self.assertEqual(BOARD_SIZE, 15)

    def test_places_and_reads_tile(self):
        board = Board()
        tile = Tile("a")
        board.place_tile((7, 7), tile)
        self.assertIs(board.tile_at((7, 7)), tile)
        self.assertTrue(board.is_occupied((7, 7)))
        self.assertEqual(board.occupied_count, 1)
        self.assertFalse(board.is_empty)

    def test_blank_keeps_represented_letter_but_scores_zero(self):
        blank = Tile("e", is_blank=True)
        self.assertEqual(blank.letter, "E")
        self.assertEqual(blank.points, 0)
        self.assertEqual(Tile("E").points, 1)

    def test_tile_rejects_invalid_letter(self):
        for value in ("", "AB", "?", "1"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Tile(value)

    def test_cannot_place_on_occupied_square(self):
        board = Board()
        board.place_tile((7, 7), Tile("A"))
        with self.assertRaises(ValueError):
            board.place_tile((7, 7), Tile("B"))
        self.assertEqual(board.tile_at((7, 7)).letter, "A")

    def test_invalid_coordinate_is_rejected(self):
        board = Board()
        for coordinate in ((-1, 0), (0, 15), (7,), "7,7"):
            with self.subTest(coordinate=coordinate):
                with self.assertRaises(ValueError):
                    board.tile_at(coordinate)

    def test_multi_tile_placement_is_atomic(self):
        board = Board()
        board.place_tile((7, 7), Tile("A"))
        with self.assertRaises(ValueError):
            board.place_tiles({
                (7, 8): Tile("B"),
                (7, 7): Tile("C"),
            })
        self.assertEqual(board.occupied_count, 1)
        self.assertIsNone(board.tile_at((7, 8)))

    def test_serialization_round_trip_including_blank(self):
        board = Board()
        board.place_tiles({
            (7, 7): Tile("A"),
            (7, 8): Tile("E", is_blank=True),
        })
        restored = Board.from_dict(board.to_dict())
        self.assertEqual(restored.occupied_count, 2)
        self.assertEqual(restored.tile_at((7, 7)), Tile("A"))
        self.assertEqual(restored.tile_at((7, 8)), Tile("E", is_blank=True))
        self.assertEqual(restored.to_dict(), board.to_dict())

    def test_import_rejects_duplicate_or_out_of_range_squares(self):
        duplicate = {
            "size": 15,
            "tiles": [
                {"row": 7, "column": 7, "letter": "A"},
                {"row": 7, "column": 7, "letter": "B"},
            ],
        }
        outside = {
            "size": 15,
            "tiles": [{"row": 15, "column": 0, "letter": "A"}],
        }
        for data in (duplicate, outside):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    Board.from_dict(data)


if __name__ == "__main__":
    unittest.main()
