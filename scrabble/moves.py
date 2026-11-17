"""Structural Scrabble move validation and scoring.

The caller supplies a dictionary as either a set-like container of uppercase
words or a callable accepting a word. If omitted, only board geometry and
scoring are checked; dictionary validation is then the caller's responsibility.
"""

from dataclasses import dataclass

from .board import Board, Tile
from .rules import BINGO_BONUS, RACK_SIZE, score_word


class InvalidMove(ValueError):
    """Raised when a proposed move violates Scrabble board rules."""


@dataclass(frozen=True)
class FormedWord:
    letters: str
    coordinates: tuple
    direction: str
    score: int


@dataclass(frozen=True)
class MoveResult:
    words: tuple
    score: int
    bingo: bool


def _word_from(board, placements, start, delta):
    """Return the maximal word through start in direction delta."""
    row, column = start
    dr, dc = delta

    # Walk backwards to the beginning of the word.
    while True:
        previous = (row - dr, column - dc)
        if not (0 <= previous[0] < 15 and 0 <= previous[1] < 15):
            break
        if previous not in placements and board.tile_at(previous) is None:
            break
        row, column = previous

    coordinates = []
    letters = []
    blanks = set()
    newly_placed = set(placements)
    current = (row, column)

    while 0 <= current[0] < 15 and 0 <= current[1] < 15:
        tile = placements.get(current)
        if tile is None:
            tile = board.tile_at(current)
        if tile is None:
            break
        coordinates.append(current)
        letters.append(tile.letter)
        if tile.is_blank:
            blanks.add(current)
        current = (current[0] + dr, current[1] + dc)

    return "".join(letters), tuple(coordinates), newly_placed, blanks


def _dictionary_contains(dictionary, word):
    if callable(dictionary):
        return bool(dictionary(word))
    return word in dictionary


def evaluate_move(board, placements, dictionary=None):
    """Validate and score a proposed placement without mutating the board.

    placements is a mapping of (row, column) to Tile. The move must be in one
    row or column, contiguous, connected to the centre/board, and form at
    least one word of two or more letters. A dictionary may be a set or a
    callable; if provided, every formed word must be present.
    """
    if not isinstance(board, Board):
        raise TypeError("board must be a Board")
    if not isinstance(placements, dict) or not placements:
        raise InvalidMove("A move must place at least one tile")

    checked = {}
    for coordinate, tile in placements.items():
        try:
            square = Board._check_coordinate(coordinate)
        except ValueError as exc:
            raise InvalidMove(str(exc)) from exc
        if square in checked:
            raise InvalidMove(f"Duplicate placement coordinate: {square}")
        if not isinstance(tile, Tile):
            raise InvalidMove("Every placement must be a Tile")
        if board.is_occupied(square):
            raise InvalidMove(f"Square is already occupied: {square}")
        checked[square] = tile

    # Check the opening-square requirement before line contiguity so an
    # opening move that misses the centre reports the primary rule violation.
    if board.is_empty and (7, 7) not in checked:
        raise InvalidMove("The opening move must cover the centre square")

    rows = {row for row, _ in checked}
    columns = {column for _, column in checked}
    if len(rows) > 1 and len(columns) > 1:
        raise InvalidMove("All tiles in a move must be in one row or one column")

    horizontal = len(rows) == 1
    ordered = sorted(checked, key=(lambda p: p[1]) if horizontal else (lambda p: p[0]))
    if len(ordered) > 1:
        fixed = ordered[0][0] if horizontal else ordered[0][1]
        low = ordered[0][1] if horizontal else ordered[0][0]
        high = ordered[-1][1] if horizontal else ordered[-1][0]
        for offset in range(low, high + 1):
            square = (fixed, offset) if horizontal else (offset, fixed)
            if square not in checked and not board.is_occupied(square):
                raise InvalidMove("Tiles in a move must be contiguous")

    if not board.is_empty:
        touches_board = any(
            board.is_occupied((row + dr, column + dc))
            for row, column in checked
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
            if 0 <= row + dr < 15 and 0 <= column + dc < 15
        )
        if not touches_board:
            raise InvalidMove("A move must connect to an existing tile")

    directions = ((0, 1, "horizontal"), (1, 0, "vertical"))
    found = {}
    for square in checked:
        for dr, dc, name in directions:
            letters, coordinates, new_squares, blanks = _word_from(
                board, checked, square, (dr, dc)
            )
            if len(coordinates) > 1:
                key = (dr, dc, coordinates)
                if key not in found:
                    found[key] = FormedWord(
                        letters=letters,
                        coordinates=coordinates,
                        direction=name,
                        score=score_word(letters, coordinates, new_squares, blanks),
                    )

    if not found:
        raise InvalidMove("A move must form a word of at least two letters")

    words = tuple(found.values())
    if dictionary is not None:
        for word in words:
            if not _dictionary_contains(dictionary, word.letters):
                raise InvalidMove(f"Word not in dictionary: {word.letters}")

    bingo = len(checked) == RACK_SIZE
    total = sum(word.score for word in words)
    if bingo:
        total += BINGO_BONUS
    return MoveResult(words=words, score=total, bingo=bingo)
