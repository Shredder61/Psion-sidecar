#!/usr/bin/env python3
"""Convert Guardian Sidecar crossword source text to Across Lite .puz files.

Uses only the Python standard library. The input is the native text emitted by
guardian_pi.make_output(), including Blanks, Across, Down and Solutions.
"""
from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path


_COORD = re.compile(r"^\((\d+)([A-Z])\)\s*(.*?)\s*$")
_LINE = re.compile(r"^Line\s+(\d+):\s*(.*)$", re.IGNORECASE)


def _clean_answer(value: str) -> str:
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
            raise ValueError(f"Malformed {section_name} entry: {raw!r}")
        row, col, value = match.groups()
        coord = (int(row) - 1, ord(col) - ord("A"))
        if coord in entries:
            raise ValueError(f"Duplicate {section_name} coordinate: {match.group(1)}{col}")
        entries[coord] = value.strip()
    return entries


def parse_guardian_source(source: str):
    """Parse Guardian native source into dimensions, blocks and clue/answer maps."""
    sections = {}
    current = None
    for raw in source.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.strip()
        if line in {"Blanks", "Across", "Down", "Solutions",
                    "Across solutions", "Down solutions"}:
            current = line
            sections.setdefault(current, [])
        elif current:
            sections[current].append(raw.rstrip())

    required = {"Blanks", "Across", "Down", "Across solutions", "Down solutions"}
    missing = required - sections.keys()
    if missing:
        raise ValueError("Missing Guardian sections: " + ", ".join(sorted(missing)))

    blank_rows = {}
    for raw in sections["Blanks"]:
        line = raw.strip()
        if not line:
            continue
        match = _LINE.match(line)
        if not match:
            raise ValueError(f"Malformed Blanks line: {raw!r}")
        row = int(match.group(1)) - 1
        cols = []
        for letter in match.group(2).split():
            if len(letter) != 1 or not letter.isalpha():
                raise ValueError(f"Invalid black-square column: {letter!r}")
            cols.append(ord(letter.upper()) - ord("A"))
        if row in blank_rows:
            raise ValueError(f"Duplicate blank-square row {row + 1}")
        blank_rows[row] = cols

    if not blank_rows or sorted(blank_rows) != list(range(len(blank_rows))):
        raise ValueError("Blank-square rows must start at 1 and be consecutive")
    height = len(blank_rows)
    width = max((c for cols in blank_rows.values() for c in cols), default=-1) + 1
    # Guardian's notation can omit the last column in intermediate rows.
    # The grid width is established by the rightmost coordinate in the clues.
    clue_coords = []
    for section in ("Across", "Down", "Across solutions", "Down solutions"):
        for raw in sections[section]:
            m = _COORD.match(raw.strip())
            if m:
                clue_coords.append(ord(m.group(2)) - ord("A"))
    width = max([width - 1, *clue_coords]) + 1
    if width < 1 or width > 255 or height > 255:
        raise ValueError("Invalid Guardian grid dimensions")

    blocks = {(r, c) for r, cols in blank_rows.items() for c in cols}
    for r, c in blocks:
        if c >= width:
            raise ValueError("Black-square coordinate outside grid")

    across_clues = _parse_entries(sections["Across"], "Across clue")
    down_clues = _parse_entries(sections["Down"], "Down clue")
    across_answers = _parse_entries(sections["Across solutions"], "Across solution")
    down_answers = _parse_entries(sections["Down solutions"], "Down solution")

    if across_clues.keys() != across_answers.keys():
        raise ValueError("Across clue and solution coordinates do not match")
    if down_clues.keys() != down_answers.keys():
        raise ValueError("Down clue and solution coordinates do not match")

    return {
        "width": width, "height": height, "blocks": blocks,
        "across_clues": across_clues, "down_clues": down_clues,
        "across_answers": {k: _clean_answer(v) for k, v in across_answers.items()},
        "down_answers": {k: _clean_answer(v) for k, v in down_answers.items()},
    }


def _number_slots(puzzle):
    width, height, blocks = puzzle["width"], puzzle["height"], puzzle["blocks"]
    across_starts, down_starts = [], []
    number = 0
    for r in range(height):
        for c in range(width):
            if (r, c) in blocks:
                continue
            starts_across = c == 0 or (r, c - 1) in blocks
            starts_down = r == 0 or (r - 1, c) in blocks
            across_length = 0
            if starts_across:
                while c + across_length < width and (r, c + across_length) not in blocks:
                    across_length += 1
            down_length = 0
            if starts_down:
                while r + down_length < height and (r + down_length, c) not in blocks:
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
    width, height, blocks = puzzle["width"], puzzle["height"], puzzle["blocks"]
    cells = [["." if (r, c) in blocks else " " for c in range(width)]
             for r in range(height)]
    across_starts, down_starts = _number_slots(puzzle)

    def place(entries, direction):
        for start, answer in entries.items():
            r, c = start
            if not (0 <= r < height and 0 <= c < width) or (r, c) in blocks:
                raise ValueError(f"{direction} answer starts outside a white cell: {start}")
            dr, dc = (0, 1) if direction == "Across" else (1, 0)
            for offset, char in enumerate(answer):
                rr, cc = r + dr * offset, c + dc * offset
                if rr >= height or cc >= width or (rr, cc) in blocks:
                    raise ValueError(f"{direction} answer runs into edge/block at {(rr + 1, cc + 1)}")
                existing = cells[rr][cc]
                if existing not in (" ", char):
                    raise ValueError(
                        f"Crossing mismatch at row {rr + 1}, column {cc + 1}: "
                        f"{existing} versus {char}"
                    )
                cells[rr][cc] = char

    place(puzzle["across_answers"], "Across")
    place(puzzle["down_answers"], "Down")

    # Every playable square must be covered by at least one answer.
    for r in range(height):
        for c in range(width):
            if cells[r][c] == " ":
                raise ValueError(f"Unfilled white square at row {r + 1}, column {c + 1}")

    expected_across = {coord for _n, coord in across_starts}
    expected_down = {coord for _n, coord in down_starts}
    if expected_across != puzzle["across_clues"].keys():
        missing = expected_across - puzzle["across_clues"].keys()
        extra = puzzle["across_clues"].keys() - expected_across
        raise ValueError(f"Across clue coordinates do not match grid slots; missing={missing}, extra={extra}")
    if expected_down != puzzle["down_clues"].keys():
        missing = expected_down - puzzle["down_clues"].keys()
        extra = puzzle["down_clues"].keys() - expected_down
        raise ValueError(f"Down clue coordinates do not match grid slots; missing={missing}, extra={extra}")

    # Validate answer length against the exact slot length.
    for direction, entries in (("Across", puzzle["across_answers"]),
                               ("Down", puzzle["down_answers"])):
        dr, dc = (0, 1) if direction == "Across" else (1, 0)
        for (r, c), answer in entries.items():
            length = 0
            while r + dr * length < height and c + dc * length < width:
                rr, cc = r + dr * length, c + dc * length
                if (rr, cc) in blocks:
                    break
                length += 1
            if length != len(answer):
                raise ValueError(
                    f"{direction} answer at row {r + 1}, column {c + 1} "
                    f"has {len(answer)} letters; grid slot has {length}"
                )

    return ["".join(row) for row in cells], across_starts, down_starts


def _cksum(data: bytes, checksum: int = 0) -> int:
    for byte in data:
        if checksum & 1:
            checksum = (checksum >> 1) + 0x8000
        else:
            checksum >>= 1
        checksum = (checksum + byte) & 0xFFFF
    return checksum


def _puz_text(value: str) -> bytes:
    # Guardian clues are expected to be representable in Windows-1252.
    return value.encode("cp1252", errors="replace")


def make_puz(puzzle, title="Guardian Crossword", author="The Guardian",
             copyright_text="The Guardian"):
    """Return a valid, unscrumbled Across Lite .puz byte string."""
    rows, across_starts, down_starts = build_solution_grid(puzzle)
    width, height = puzzle["width"], puzzle["height"]
    solution = "".join(rows).encode("ascii")
    player = bytes(ord("-") if ch != "." else ord(".") for ch in solution)

    ordered_clues = []
    for direction, starts, clue_map in (
        ("Across", across_starts, puzzle["across_clues"]),
        ("Down", down_starts, puzzle["down_clues"]),
    ):
        for _number, coord in starts:
            ordered_clues.append(clue_map[coord])

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
        value + b"\0" for value in (title_b, author_b, copyright_b)
    )
    strings += b"".join(value + b"\0" for value in clue_bytes)
    strings += notes_b + b"\0"

    body = solution + player + strings
    overall = _cksum(body, cib)
    struct.pack_into("<H", header, 0x00, overall)
    return bytes(header) + body


def convert_file(source_path, output_path, title=None):
    source_path = Path(source_path)
    output_path = Path(output_path)
    puzzle = parse_guardian_source(source_path.read_text(encoding="utf-8"))
    title = title or f"Guardian Crossword - {source_path.stem.replace('_', ' ')}"
    data = make_puz(puzzle, title=title)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return puzzle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Guardian native source text")
    parser.add_argument("output", help="Output .puz file")
    parser.add_argument("--title", default=None)
    args = parser.parse_args()
    puzzle = convert_file(args.source, args.output, args.title)
    print(f"Created {args.output}: {puzzle['width']}x{puzzle['height']}, "
          f"{len(puzzle['across_clues'])} Across, {len(puzzle['down_clues'])} Down")


if __name__ == "__main__":
    main()
