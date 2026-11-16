
#!/usr/bin/env python3
"""Convert Guardian crossword source text to Across Lite .puz files."""

from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path

_COORD = re.compile(r"^\((\d+)([A-Z])\)\s*(.*?)\s*$")
_LINE = re.compile(r"^Line\s+(\d+):\s*(.*)$", re.IGNORECASE)


def _clean_answer(value):
    answer = re.sub(r"[^A-Za-z]", "", value).upper()
    if not answer:
        raise ValueError("Empty crossword solution")
    return answer


def _parse_entries(lines, section_name):
    entries = {}
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        match = _COORD.match(line)
        if not match:
            raise ValueError(
                "Malformed %s entry: %r" % (section_name, raw)
            )
        row, col, value = match.groups()
        coord = (int(row) - 1, ord(col) - ord("A"))
        if coord in entries:
            raise ValueError(
                "Duplicate %s coordinate: %s%s"
                % (section_name, row, col)
            )
        entries[coord] = value.strip()
    return entries


def parse_guardian_source(source):
    """Parse Guardian source into grid dimensions, clues and solutions."""
    sections = {}
    current = None

    for raw in source.replace("\r\n", "\n").replace(
            "\r", "\n").split("\n"):
        line = raw.strip()
        if line in {
            "Blanks", "Across", "Down", "Solutions",
            "Across solutions", "Down solutions"
        }:
            current = line
            sections.setdefault(current, [])
        elif current:
            sections[current].append(raw.rstrip())

    required = {"Blanks", "Across", "Down"}
    missing = required - sections.keys()
    if missing:
        raise ValueError(
            "Missing Guardian sections: " + ", ".join(sorted(missing))
        )

    blank_rows = {}
    for raw in sections["Blanks"]:
        line = raw.strip()
        if not line:
            continue
        match = _LINE.match(line)
        if not match:
            raise ValueError("Malformed Blanks line: %r" % raw)

        row = int(match.group(1)) - 1
        cols = []
        for letter in match.group(2).split():
            if len(letter) != 1 or not letter.isalpha():
                raise ValueError(
                    "Invalid black-square column: %r" % letter
                )
            cols.append(ord(letter.upper()) - ord("A"))

        if row in blank_rows:
            raise ValueError("Duplicate blank-square row %d" % (row + 1))
        blank_rows[row] = cols

    if not blank_rows or sorted(blank_rows) != list(range(len(blank_rows))):
        raise ValueError("Blank-square rows must start at 1 and be consecutive")

    height = len(blank_rows)
    width_from_blocks = max(
        (c for cols in blank_rows.values() for c in cols),
        default=-1
    ) + 1

    clue_coords = []
    for section in (
        "Across", "Down", "Across solutions", "Down solutions"
    ):
        for raw in sections.get(section, []):
            match = _COORD.match(raw.strip())
            if match:
                clue_coords.append(ord(match.group(2)) - ord("A"))

    width = max([width_from_blocks - 1] + clue_coords) + 1

    if width < 1 or width > 255 or height > 255:
        raise ValueError("Invalid Guardian grid dimensions")

    blocks = {
        (r, c)
        for r, cols in blank_rows.items()
        for c in cols
    }

    for r, c in blocks:
        if c >= width:
            raise ValueError("Black-square coordinate outside grid")

    across_clues = _parse_entries(sections["Across"], "Across clue")
    down_clues = _parse_entries(sections["Down"], "Down clue")

    across_answers = _parse_entries(
        sections.get("Across solutions", []), "Across solution"
    )
    down_answers = _parse_entries(
        sections.get("Down solutions", []), "Down solution"
    )

    has_solutions = bool(across_answers or down_answers)

    if has_solutions:
        if across_clues.keys() != across_answers.keys():
            raise ValueError(
                "Across clue and solution coordinates do not match"
            )
        if down_clues.keys() != down_answers.keys():
            raise ValueError(
                "Down clue and solution coordinates do not match"
            )

        across_answers = {
            k: _clean_answer(v) for k, v in across_answers.items()
        }
        down_answers = {
            k: _clean_answer(v) for k, v in down_answers.items()
        }

    return {
        "width": width,
        "height": height,
        "blocks": blocks,
        "across_clues": across_clues,
        "down_clues": down_clues,
        "across_answers": across_answers,
        "down_answers": down_answers,
        "has_solutions": has_solutions,
    }


def _number_slots(puzzle):
    width = puzzle["width"]
    height = puzzle["height"]
    blocks = puzzle["blocks"]

    across_starts = []
    down_starts = []
    number = 0

    for r in range(height):
        for c in range(width):
            if (r, c) in blocks:
                continue

            starts_across = c == 0 or (r, c - 1) in blocks
            starts_down = r == 0 or (r - 1, c) in blocks

            across_length = 0
            if starts_across:
                while (
                    c + across_length < width
                    and (r, c + across_length) not in blocks
                ):
                    across_length += 1

            down_length = 0
            if starts_down:
                while (
                    r + down_length < height
                    and (r + down_length, c) not in blocks
                ):
                    down_length += 1

            has_across = starts_across and across_length >= 2
            has_down = starts_down and down_length >= 2

            if has_across or has_down:
                number += 1
                if has_across:
                    across_starts.append((number, (r, c)))
                if has_down:
                    down_starts.append((number, (r, c)))

    return across_starts, down_starts


def build_solution_grid(puzzle):
    """Build and validate the solution grid."""
    width = puzzle["width"]
    height = puzzle["height"]
    blocks = puzzle["blocks"]

    cells = [
        ["." if (r, c) in blocks else " " for c in range(width)]
        for r in range(height)
    ]

    across_starts, down_starts = _number_slots(puzzle)

    if not puzzle["has_solutions"]:
        # A clue-only puzzle has no known solution letters.
        rows = [
            "".join("." if cell == "." else "-" for cell in row)
            for row in cells
        ]
        return rows, across_starts, down_starts

    def place(entries, direction):
        for start, answer in entries.items():
            r, c = start

            if not (0 <= r < height and 0 <= c < width):
                raise ValueError(
                    "%s answer starts outside grid: %r" % (direction, start)
                )
            if (r, c) in blocks:
                raise ValueError(
                    "%s answer starts on a black square: %r"
                    % (direction, start)
                )

            dr, dc = (0, 1) if direction == "Across" else (1, 0)

            for offset, char in enumerate(answer):
                rr = r + dr * offset
                cc = c + dc * offset

                if (
                    rr >= height or cc >= width
                    or (rr, cc) in blocks
                ):
                    raise ValueError(
                        "%s answer runs into edge/block at row %d, column %d"
                        % (direction, rr + 1, cc + 1)
                    )

                existing = cells[rr][cc]
                if existing not in (" ", char):
                    raise ValueError(
                        "Crossing mismatch at row %d, column %d: %s versus %s"
                        % (rr + 1, cc + 1, existing, char)
                    )
                cells[rr][cc] = char

    place(puzzle["across_answers"], "Across")
    place(puzzle["down_answers"], "Down")

    for r in range(height):
        for c in range(width):
            if cells[r][c] == " ":
                raise ValueError(
                    "Unfilled white square at row %d, column %d"
                    % (r + 1, c + 1)
                )

    expected_across = {coord for _, coord in across_starts}
    expected_down = {coord for _, coord in down_starts}

    if expected_across != puzzle["across_clues"].keys():
        raise ValueError("Across clue coordinates do not match grid slots")

    if expected_down != puzzle["down_clues"].keys():
        raise ValueError("Down clue coordinates do not match grid slots")

    for direction, entries in (
        ("Across", puzzle["across_answers"]),
        ("Down", puzzle["down_answers"])
    ):
        dr, dc = (0, 1) if direction == "Across" else (1, 0)

        for (r, c), answer in entries.items():
            length = 0
            while r + dr * length < height and c + dc * length < width:
                rr = r + dr * length
                cc = c + dc * length
                if (rr, cc) in blocks:
                    break
                length += 1

            if length != len(answer):
                raise ValueError(
                    "%s answer at row %d, column %d has %d letters; "
                    "grid slot has %d"
                    % (direction, r + 1, c + 1, len(answer), length)
                )

    return ["".join(row) for row in cells], across_starts, down_starts


def _cksum(data, checksum=0):
    for byte in data:
        if checksum & 1:
            checksum = (checksum >> 1) + 0x8000
        else:
            checksum >>= 1
        checksum = (checksum + byte) & 0xFFFF
    return checksum


def _puz_text(value):
    return value.encode("cp1252", errors="replace")


def make_puz(
    puzzle,
    title="Guardian Crossword",
    author="The Guardian",
    copyright_text="The Guardian"
):
    """Return an Across Lite .puz byte string."""
    rows, across_starts, down_starts = build_solution_grid(puzzle)

    width = puzzle["width"]
    height = puzzle["height"]

    solution = "".join(rows).encode("ascii")
    player = bytes(
        ord("-") if ch != "." else ord(".")
        for ch in solution
    )

    # Across Lite stores clue strings in puzzle-number order, not in
    # separate Across and Down groups. When a number has both directions,
    # its Across clue must precede its Down clue. Keep the Guardian clue
    # coordinates and grid numbering unchanged; only build the PUZ clue
    # string table in the order required by the file format.
    across_by_number = {
        number: puzzle["across_clues"][coord]
        for number, coord in across_starts
    }
    down_by_number = {
        number: puzzle["down_clues"][coord]
        for number, coord in down_starts
    }

    ordered_clues = []
    for number in sorted(set(across_by_number) | set(down_by_number)):
        if number in across_by_number:
            ordered_clues.append(across_by_number[number])
        if number in down_by_number:
            ordered_clues.append(down_by_number[number])

    title_b, author_b, copyright_b = map(
        _puz_text, (title, author, copyright_text)
    )
    clue_bytes = [_puz_text(clue) for clue in ordered_clues]
    notes_b = b""

    header = bytearray(0x34)
    header[2:14] = b"ACROSS&DOWN\0"
    header[0x18:0x1C] = b"1.3\0"
    header[0x2C] = width
    header[0x2D] = height
    struct.pack_into("<H", header, 0x2E, len(ordered_clues))
    struct.pack_into("<H", header, 0x30, 0)
    struct.pack_into("<H", header, 0x32, 0)

    cib = _cksum(bytes(header[0x2C:0x34]))
    struct.pack_into("<H", header, 0x0E, cib)

    c_sol = _cksum(solution)
    c_grid = _cksum(player)

    partial = 0
    for value in (title_b, author_b, copyright_b):
        if value:
            partial = _cksum(value + b"\0", partial)

    for clue in clue_bytes:
        partial = _cksum(clue, partial)

    if notes_b:
        partial = _cksum(notes_b + b"\0", partial)

    masks = (0x49, 0x43, 0x48, 0x45)
    highs = (0x41, 0x54, 0x45, 0x44)
    checks = (cib, c_sol, c_grid, partial)

    for i, (mask, value) in enumerate(zip(masks, checks)):
        header[0x10 + i] = mask ^ (value & 0xFF)

    for i, (mask, value) in enumerate(zip(highs, checks)):
        header[0x14 + i] = mask ^ ((value >> 8) & 0xFF)

    strings = b"".join(
        value + b"\0"
        for value in (title_b, author_b, copyright_b)
    )
    strings += b"".join(value + b"\0" for value in clue_bytes)
    strings += notes_b + b"\0"

    body = solution + player + strings
    overall = _cksum(body, cib)
    struct.pack_into("<H", header, 0x00, overall)

    return bytes(header) + body


def convert_source(source, output_path, title="Guardian Crossword"):
    """Convert Guardian source held in memory and save only the PUZ file."""
    output_path = Path(output_path)
    puzzle = parse_guardian_source(source)
    data = make_puz(puzzle, title=title)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)

    return puzzle


def convert_file(source_path, output_path, title=None):
    source_path = Path(source_path)
    title = title or (
        "Guardian Crossword - "
        + source_path.stem.replace("_", " ")
    )

    return convert_source(
        source_path.read_text(encoding="utf-8"),
        output_path,
        title
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Guardian native source text")
    parser.add_argument("output", help="Output .puz file")
    parser.add_argument("--title", default=None)
    args = parser.parse_args()

    puzzle = convert_file(args.source, args.output, args.title)

    print(
        "Created %s: %dx%d, %d Across, %d Down, solutions: %s"
        % (
            args.output,
            puzzle["width"],
            puzzle["height"],
            len(puzzle["across_clues"]),
            len(puzzle["down_clues"]),
            "yes" if puzzle["has_solutions"] else "no"
        )
    )


if __name__ == "__main__":
    main()
