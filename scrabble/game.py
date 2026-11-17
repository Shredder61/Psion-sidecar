"""Game state for a local Scrabble game.

The game engine owns the bag, racks, scores and turn order. Board and move
validation remain in their own modules. No browser or server dependencies.
"""

import random

from .board import Board, Tile
from .dictionary import WordDictionary
from .moves import evaluate_move
from .rules import LETTER_VALUES, RACK_SIZE, new_bag


class GameError(ValueError):
    """Raised when a requested game action is not allowed."""


def _rack_tile_key(tile):
    return "?" if tile.is_blank else tile.letter


def _tile_points(tile):
    return 0 if tile.is_blank else LETTER_VALUES[tile.letter]


class Player:
    def __init__(self, name, rack=None, score=0):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Player name must be non-empty text")
        self.name = name.strip()
        self.rack = list(rack or [])
        if any(tile not in LETTER_VALUES for tile in self.rack):
            raise ValueError("Rack contains an unknown tile")
        if len(self.rack) > RACK_SIZE:
            raise ValueError("A rack cannot contain more than seven tiles")
        self.score = int(score)

    def to_dict(self):
        return {"name": self.name, "rack": list(self.rack), "score": self.score}

    @classmethod
    def from_dict(cls, data):
        return cls(data["name"], data["rack"], data["score"])


class Game:
    """A complete in-memory game. Create with Game.new_game(names, seed=...)."""

    SAVE_VERSION = 1

    def __init__(self, players, bag, board=None, current_player=0,
                 consecutive_passes=0, ended=False):
        if not 2 <= len(players) <= 4:
            raise ValueError("A game requires two to four players")
        self.players = list(players)
        self.bag = list(bag)
        if any(tile not in LETTER_VALUES for tile in self.bag):
            raise ValueError("Bag contains an unknown tile")
        self.board = board if board is not None else Board()
        if not 0 <= current_player < len(self.players):
            raise ValueError("Current player index is invalid")
        self.current_player = current_player
        self.consecutive_passes = int(consecutive_passes)
        self.ended = bool(ended)
        self._rng = random.Random()

    @classmethod
    def new_game(cls, names, seed=None):
        names = list(names)
        if not 2 <= len(names) <= 4:
            raise ValueError("A game requires two to four players")
        rng = random.Random(seed)
        bag = new_bag()
        rng.shuffle(bag)
        players = [Player(name) for name in names]
        game = cls(players, bag)
        game._rng = rng
        for player in players:
            game._draw_to_rack(player)
        return game

    @property
    def player(self):
        return self.players[self.current_player]

    def _draw_to_rack(self, player):
        while len(player.rack) < RACK_SIZE and self.bag:
            player.rack.append(self.bag.pop())

    def _advance_turn(self):
        self.current_player = (self.current_player + 1) % len(self.players)

    def _finish_if_out(self, player_who_used_last_tile):
        if (
            player_who_used_last_tile is not None
            and not self.bag
            and not player_who_used_last_tile.rack
        ):
            self.ended = True
            for player in self.players:
                if player is player_who_used_last_tile:
                    continue
                penalty = sum(LETTER_VALUES[tile] for tile in player.rack)
                player.score -= penalty
                player_who_used_last_tile.score += penalty
        elif self.consecutive_passes >= len(self.players) * 2:
            self.ended = True

    def play_move(self, placements, dictionary=None):
        """Validate, commit, score and replenish the current player's move.

        placements maps board coordinates to Tile objects. Blank tiles in the
        rack are represented by '?'; their board Tile stores the chosen letter
        with is_blank=True.
        """
        if self.ended:
            raise GameError("The game has ended")

        player = self.player
        needed = {}
        for tile in placements.values():
            key = _rack_tile_key(tile)
            needed[key] = needed.get(key, 0) + 1
        available = {}
        for tile in player.rack:
            available[tile] = available.get(tile, 0) + 1
        for tile, count in needed.items():
            if available.get(tile, 0) < count:
                raise GameError(f"Tile not available in rack: {tile}")

        result = evaluate_move(self.board, placements, dictionary)
        # No state is changed until all validation has succeeded.
        self.board.place_tiles(placements)
        for tile, count in needed.items():
            for _ in range(count):
                player.rack.remove(tile)
        player.score += result.score
        self.consecutive_passes = 0
        self._draw_to_rack(player)
        self._finish_if_out(player)
        if not self.ended:
            self._advance_turn()
        return result

    def pass_turn(self):
        if self.ended:
            raise GameError("The game has ended")
        self.consecutive_passes += 1
        self._advance_turn()
        self._finish_if_out(None)

    def exchange_tiles(self, tiles):
        """Exchange selected rack letters; the bag must contain enough tiles."""
        if self.ended:
            raise GameError("The game has ended")
        tiles = list(tiles)
        if not tiles:
            raise GameError("Select at least one tile to exchange")
        if len(tiles) > len(self.player.rack):
            raise GameError("Cannot exchange more tiles than are in the rack")
        if len(self.bag) < len(tiles):
            raise GameError("Not enough tiles remain in the bag to exchange")
        remaining = list(self.player.rack)
        try:
            for tile in tiles:
                remaining.remove(tile)
        except ValueError as exc:
            raise GameError("Selected exchange tile is not in the rack") from exc

        # Draw replacements before returning exchanged tiles, as in Scrabble.
        replacements = [self.bag.pop() for _ in tiles]
        self.bag.extend(tiles)
        self._rng.shuffle(self.bag)
        self.player.rack = remaining + replacements
        self.consecutive_passes = 0
        self._advance_turn()

    def to_dict(self):
        return {
            "version": self.SAVE_VERSION,
            "players": [player.to_dict() for player in self.players],
            "bag": list(self.bag),
            "board": self.board.to_dict(),
            "current_player": self.current_player,
            "consecutive_passes": self.consecutive_passes,
            "ended": self.ended,
        }

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or data.get("version") != cls.SAVE_VERSION:
            raise ValueError("Unsupported or invalid saved game version")
        players = [Player.from_dict(player) for player in data["players"]]
        board = Board.from_dict(data["board"])
        game = cls(
            players=players,
            bag=data["bag"],
            board=board,
            current_player=data["current_player"],
            consecutive_passes=data["consecutive_passes"],
            ended=data["ended"],
        )
        return game
