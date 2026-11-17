import unittest

from scrabble.board import Tile
from scrabble.game import Game, GameError
from scrabble.rules import LETTER_DISTRIBUTION


class GameTests(unittest.TestCase):
    def test_new_game_deals_seven_tiles_each(self):
        game = Game.new_game(["Alice", "Bob"], seed=7)
        self.assertEqual([len(p.rack) for p in game.players], [7, 7])
        self.assertEqual(len(game.bag), 86)
        self.assertEqual(game.current_player, 0)

    def test_full_tile_set_is_conserved_after_deal(self):
        game = Game.new_game(["Alice", "Bob"], seed=3)
        counts = {}
        for tile in game.bag + [t for p in game.players for t in p.rack]:
            counts[tile] = counts.get(tile, 0) + 1
        self.assertEqual(counts, LETTER_DISTRIBUTION)

    def test_requires_two_to_four_players(self):
        for names in ([], ["Alice"], ["A", "B", "C", "D", "E"]):
            with self.subTest(names=names):
                with self.assertRaises(ValueError):
                    Game.new_game(names)

    def test_valid_move_scores_replenishes_and_advances(self):
        game = Game.new_game(["Alice", "Bob"], seed=1)
        game.players[0].rack = list("CATXXXX")
        game.bag = list("EEEE")
        result = game.play_move({
            (7, 6): Tile("C"), (7, 7): Tile("A"), (7, 8): Tile("T")
        }, {"CAT"})
        self.assertEqual(result.score, 10)
        self.assertEqual(game.players[0].score, 10)
        self.assertEqual(len(game.players[0].rack), 7)
        self.assertEqual(game.current_player, 1)
        self.assertEqual(len(game.bag), 1)

    def test_move_cannot_use_tile_not_in_rack(self):
        game = Game.new_game(["Alice", "Bob"], seed=2)
        before = game.to_dict()
        with self.assertRaisesRegex(GameError, "not available"):
            game.play_move({(7, 7): Tile("Z")})
        self.assertEqual(game.to_dict(), before)

    def test_invalid_move_does_not_change_game_state(self):
        game = Game.new_game(["Alice", "Bob"], seed=4)
        game.players[0].rack = list("CATXXXX")
        before_score = game.player.score
        before_rack = list(game.player.rack)
        with self.assertRaises(ValueError):
            game.play_move({(7, 6): Tile("C"), (7, 8): Tile("T")})
        self.assertTrue(game.board.is_empty)
        self.assertEqual(game.player.score, before_score)
        self.assertEqual(game.player.rack, before_rack)

    def test_blank_in_rack_can_represent_any_letter(self):
        game = Game.new_game(["Alice", "Bob"], seed=5)
        game.players[0].rack = ["?", "A", "X", "X", "X", "X", "X"]
        result = game.play_move({
            (7, 7): Tile("C", is_blank=True),
            (7, 8): Tile("A"),
        }, {"CA"})
        self.assertEqual(result.score, 2)
        self.assertNotIn("?", game.board.to_dict().__repr__())

    def test_pass_advances_and_two_rounds_end_game(self):
        game = Game.new_game(["Alice", "Bob"], seed=6)
        game.pass_turn()
        self.assertEqual(game.current_player, 1)
        game.pass_turn()
        game.pass_turn()
        game.pass_turn()
        self.assertTrue(game.ended)

    def test_exchange_draws_before_returning_tiles(self):
        game = Game.new_game(["Alice", "Bob"], seed=9)
        game.players[0].rack = list("ABCDEFG")
        game.bag = list("XYZ")
        game.exchange_tiles(["A", "B"])
        self.assertEqual(len(game.player.rack), 7)
        self.assertEqual(len(game.bag), 3)
        self.assertNotIn("A", game.player.rack)
        self.assertNotIn("B", game.player.rack)
        self.assertEqual(game.current_player, 1)

    def test_exchange_requires_enough_bag_tiles(self):
        game = Game.new_game(["Alice", "Bob"], seed=10)
        game.bag = ["A"]
        before = game.to_dict()
        with self.assertRaisesRegex(GameError, "Not enough"):
            game.exchange_tiles(["A", "B"])
        self.assertEqual(game.to_dict(), before)

    def test_save_restore_round_trip(self):
        game = Game.new_game(["Alice", "Bob"], seed=11)
        game.players[0].rack = ["?", "A", "B", "C", "D", "E", "F"]
        game.play_move({
            (7, 7): Tile("C", is_blank=True),
            (7, 8): Tile("A"),
        }, {"CA"})
        restored = Game.from_dict(game.to_dict())
        self.assertEqual(restored.to_dict(), game.to_dict())

    def test_rejects_unsupported_save_version(self):
        with self.assertRaisesRegex(ValueError, "version"):
            Game.from_dict({"version": 99})


if __name__ == "__main__":
    unittest.main()
