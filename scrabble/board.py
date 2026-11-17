"""The 15x15 Scrabble board and its tile representation.

Coordinates are zero-based (row, column). The centre is (7, 7).
This module contains no web or platform dependencies.
"""

from dataclasses import dataclass

from .rules import BOARD_SIZE


@dataclass(frozen=True)
class Tile:
    """A tile as it appears on the board.

    A blank stores the letter it represents, but always has a value of zero.
    """

    letter: str
    is_blank: bool = False

    def __post_init__(self):
        letter = self.letter.upper()
        if len(letter) != 1 or letter not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            raise ValueError("A board tile must represent one letter A-Z")
        object.__setattr__(self, "letter", letter)

    @property
    def points(self):
        """Return the tile's face value (zero for a blank)."""
        if self.is_blank:
            return 0
        from .rules import LETTER_VALUES
        return LETTER_VALUES[self.letter]

    def to_dict(self):
        return {"letter": self.letter, "is_blank": self.is_blank}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError("Tile data must be an object")
        return cls(data["letter"], data.get("is_blank", False))


class Board:
    """A 15x15 board. Empty squares contain None; occupied squares contain Tile."""

    def __init__(self):
        self._grid = [
            [None for _ in range(BOARD_SIZE)]
            for _ in range(BOARD_SIZE)
        ]

    @staticmethod
    def _check_coordinate(coordinate):
        if (
            not isinstance(coordinate, (tuple, list))
            or len(coordinate) != 2
            or any(not isinstance(value, int) for value in coordinate)
        ):
            raise ValueError("A coordinate must be a (row, column) pair")
        row, column = coordinate
        if not (0 <= row < BOARD_SIZE and 0 <= column < BOARD_SIZE):
            raise ValueError(f"Coordinate outside the board: {coordinate}")
        return row, column

    def tile_at(self, coordinate):
        row, column = self._check_coordinate(coordinate)
        return self._grid[row][column]

    def is_occupied(self, coordinate):
        return self.tile_at(coordinate) is not None

    @property
    def occupied_count(self):
        return sum(tile is not None for row in self._grid for tile in row)

    @property
    def is_empty(self):
        return self.occupied_count == 0

    def place_tile(self, coordinate, tile):
        """Place one tile; reject invalid or already occupied squares."""
        self.place_tiles({coordinate: tile})

    def place_tiles(self, placements):
        """Atomically place a mapping of coordinates to Tile objects.

        All placements are checked before the board is changed.
        """
        if not isinstance(placements, dict) or not placements:
            raise ValueError("At least one tile placement is required")

        checked = []
        seen = set()
        for coordinate, tile in placements.items():
            square = self._check_coordinate(coordinate)
            if square in seen:
                raise ValueError(f"Duplicate placement coordinate: {square}")
            seen.add(square)
            if not isinstance(tile, Tile):
                raise ValueError("Every placement must contain a Tile")
            if self._grid[square[0]][square[1]] is not None:
                raise ValueError(f"Square is already occupied: {square}")
            checked.append((square, tile))

        for (row, column), tile in checked:
            self._grid[row][column] = tile

    def iter_tiles(self):
        """Yield ((row, column), tile) pairs in board reading order."""
        for row in range(BOARD_SIZE):
            for column in range(BOARD_SIZE):
                tile = self._grid[row][column]
                if tile is not None:
                    yield (row, column), tile

    def to_dict(self):
        """Return a JSON-compatible representation of the board."""
        return {
            "size": BOARD_SIZE,
            "tiles": [
                {"row": row, "column": column, **tile.to_dict()}
                for (row, column), tile in self.iter_tiles()
            ],
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild a board from to_dict() output, rejecting malformed data."""
        if not isinstance(data, dict) or data.get("size") != BOARD_SIZE:
            raise ValueError("Board data must describe a 15x15 board")
        entries = data.get("tiles")
        if not isinstance(entries, list):
            raise ValueError("Board tiles must be a list")

        board = cls()
        placements = {}
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Each board tile must be an object")
            coordinate = (entry.get("row"), entry.get("column"))
            if coordinate in placements:
                raise ValueError(f"Duplicate tile coordinate: {coordinate}")
            placements[coordinate] = Tile.from_dict(entry)
        if placements:
            board.place_tiles(placements)
        return board
