"""Standard English Scrabble tile and board constants.

Coordinates are zero-based (row, column), with (7, 7) at the centre.
This module deliberately contains no web or platform dependencies.
"""

from collections import Counter

BOARD_SIZE = 15
RACK_SIZE = 7
BINGO_BONUS = 50

# Standard English distribution: 98 letter tiles plus two blanks.
LETTER_DISTRIBUTION = {
    "A": 9, "B": 2, "C": 2, "D": 4, "E": 12,
    "F": 2, "G": 3, "H": 2, "I": 9, "J": 1,
    "K": 1, "L": 4, "M": 2, "N": 6, "O": 8,
    "P": 2, "Q": 1, "R": 6, "S": 4, "T": 6,
    "U": 4, "V": 2, "W": 2, "X": 1, "Y": 2,
    "Z": 1, "?": 2,
}

LETTER_VALUES = {
    **{letter: 1 for letter in "AEILNORSTU"},
    **{letter: 2 for letter in "DG"},
    **{letter: 3 for letter in "BCMP"},
    **{letter: 4 for letter in "FHVWY"},
    "K": 5, "J": 8, "X": 8, "Q": 10, "Z": 10,
    "?": 0,
}

# Premium squares are represented as (row, column): multiplier.
# A word multiplier applies to the complete word; a letter multiplier
# applies only to a newly placed tile on that square.
TRIPLE_WORD = frozenset({
    (0, 0), (0, 7), (0, 14), (7, 0), (7, 14),
    (14, 0), (14, 7), (14, 14),
})
DOUBLE_WORD = frozenset({
    (1, 1), (2, 2), (3, 3), (4, 4),
    (1, 13), (2, 12), (3, 11), (4, 10),
    (10, 4), (11, 3), (12, 2), (13, 1),
    (10, 10), (11, 11), (12, 12), (13, 13),
    (7, 7),
})
TRIPLE_LETTER = frozenset({
    (1, 5), (1, 9), (5, 1), (5, 5), (5, 9), (5, 13),
    (9, 1), (9, 5), (9, 9), (9, 13),
    (13, 5), (13, 9),
})
DOUBLE_LETTER = frozenset({
    (0, 3), (0, 11), (2, 6), (2, 8),
    (3, 0), (3, 7), (3, 14),
    (6, 2), (6, 6), (6, 8), (6, 12),
    (7, 3), (7, 11),
    (8, 2), (8, 6), (8, 8), (8, 12),
    (11, 0), (11, 7), (11, 14),
    (12, 6), (12, 8), (14, 3), (14, 11),
})

PREMIUM_SQUARES = {
    **{square: ("TW", 3) for square in TRIPLE_WORD},
    **{square: ("DW", 2) for square in DOUBLE_WORD},
    **{square: ("TL", 3) for square in TRIPLE_LETTER},
    **{square: ("DL", 2) for square in DOUBLE_LETTER},
}


def new_bag():
    """Return a fresh mutable list containing the standard 100 tiles."""
    return [
        letter
        for letter, count in LETTER_DISTRIBUTION.items()
        for _ in range(count)
    ]


def validate_tile_distribution():
    """Raise ValueError if the configured English set is not 100 tiles."""
    total = sum(LETTER_DISTRIBUTION.values())
    if total != 100:
        raise ValueError(f"English tile distribution must total 100, got {total}")
    if set(LETTER_DISTRIBUTION) != set(LETTER_VALUES):
        raise ValueError("Every distributed tile must have exactly one point value")
    return True


def score_word(letters, coordinates, newly_placed, blank_squares=()):
    """Score one word, applying premiums only to newly placed tiles.

    Args:
        letters: letters in word order (use the represented letter for blanks).
        coordinates: matching (row, column) positions.
        newly_placed: coordinates occupied by tiles placed this turn.
        blank_squares: newly placed coordinates occupied by blank tiles.

    Cross-word scores are calculated separately by the move engine.
    """
    if len(letters) != len(coordinates):
        raise ValueError("letters and coordinates must have equal length")

    new = set(newly_placed)
    blanks = set(blank_squares)
    base_total = 0
    word_multiplier = 1

    for letter, square in zip(letters.upper(), coordinates):
        if square in new:
            value = 0 if square in blanks else LETTER_VALUES[letter]
            premium, multiplier = PREMIUM_SQUARES.get(square, (None, 1))
            if premium == "DL":
                value *= 2
            elif premium == "TL":
                value *= 3
            if premium == "DW":
                word_multiplier *= 2
            elif premium == "TW":
                word_multiplier *= 3
        else:
            value = LETTER_VALUES[letter]
        base_total += value

    return base_total * word_multiplier
