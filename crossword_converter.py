#!/usr/bin/env python3
"""Convert Guardian crossword text files to RMR Crossword text format."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

LINE_RE = re.compile(r"^Line\s+(\d+)\s*:\s*(.*)$", re.IGNORECASE)
ENTRY_RE = re.compile(r"^\((\d+)([A-Z])\)\s*(.*)$")


def parse_entries(lines: list[str]) -> dict[tuple[int, int], str]:
    entries: dict[tuple[int, int], str] = {}
    for line in lines:
        match = ENTRY_RE.match(line.strip())
        if not match:
            continue
        row = int(match.group(1))
        col = ord(match.group(2).upper()) - ord("A") + 1
        answer = re.sub(r"[^A-Za-z]", "", match.group(3)).upper()
        if answer:
            entries[(row, col)] = answer
    return entries


def convert_text(source: str) -> str:
    lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    grid_data: dict[int, str] = {}

    for line in lines:
        match = LINE_RE.match(line.strip())
        if match:
            grid_data[int(match.group(1))] = match.group(2).strip()

    if not grid_data:
        raise ValueError(
            "No Guardian grid rows ('Line 1:', 'Line 2:', ...) were found."
        )

    row_count = max(grid_data)
    if sorted(grid_data) != list(range(1, row_count + 1)):
        raise ValueError(
            "Guardian grid rows are missing or not numbered consecutively."
        )

    width = row_count
    grid: list[list[str]] = []

    for row_num in range(1, row_count + 1):
        cells = ["-"] * width
        for letter in re.findall(r"[A-Z]", grid_data[row_num].upper()):
            col = ord(letter) - ord("A") + 1
            if col <= width:
                cells[col - 1] = "#"
        grid.append(cells)

    try:
        across_idx = next(
            i for i, line in enumerate(lines)
            if line.strip() == "Across"
        )
        down_idx = next(
            i for i, line in enumerate(lines)
            if i > across_idx and line.strip() == "Down"
        )
        solutions_idx = next(
            i for i, line in enumerate(lines)
            if i > down_idx and line.strip() == "Solutions"
        )
    except StopIteration as exc:
        raise ValueError(
            "Could not find the Across, Down and Solutions sections."
        ) from exc

    across_clues = [
        line.strip()
        for line in lines[across_idx + 1:down_idx]
        if line.strip()
    ]
    down_clues = [
        line.strip()
        for line in lines[down_idx + 1:solutions_idx]
        if line.strip()
    ]

    across_sol_idx = next(
        (
            i for i in range(solutions_idx + 1, len(lines))
            if lines[i].strip() == "Across solutions"
        ),
        None,
    )
    down_sol_idx = next(
        (
            i for i in range(solutions_idx + 1, len(lines))
            if lines[i].strip() == "Down solutions"
        ),
        None,
    )

    if (
        across_sol_idx is None
        or down_sol_idx is None
        or down_sol_idx < across_sol_idx
    ):
        raise ValueError(
            "Could not find both Across solutions and Down solutions sections."
        )

    across_solutions = parse_entries(
        lines[across_sol_idx + 1:down_sol_idx]
    )
    down_solutions = parse_entries(lines[down_sol_idx + 1:])

    def place(row: int, col: int, answer: str, direction: str) -> None:
        if row < 1 or row > row_count or col < 1 or col > width:
            raise ValueError(
                f"Solution starts outside the grid: ({row},{col}) {answer}"
            )

        for offset, char in enumerate(answer):
            r = row - 1 + (offset if direction == "down" else 0)
            c = col - 1 + (offset if direction == "across" else 0)

            if r >= row_count or c >= width:
                raise ValueError(
                    f"Solution runs outside the grid: ({row},{col}) {answer}"
                )

            if grid[r][c] == "#":
                raise ValueError(
                    f"Solution {answer} crosses a black square at "
                    f"row {r+1}, column {c+1}."
                )

            if grid[r][c] not in ("-", char):
                raise ValueError(
                    f"Conflicting answers at row {r+1}, column {c+1}: "
                    f"{grid[r][c]} versus {char} from {answer}."
                )

            grid[r][c] = char

    for (row, col), answer in across_solutions.items():
        place(row, col, answer, "across")

    for (row, col), answer in down_solutions.items():
        place(row, col, answer, "down")

    output = [
        "<grid>",
        *("".join(row) for row in grid),
        "<across>",
        *across_clues,
        "<down>",
        *down_clues,
    ]

    return "\n".join(output) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Guardian crossword .txt file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="output path (default: INPUT_converted.txt)",
    )
    args = parser.parse_args()

    output_path = args.output or args.input.with_name(
        args.input.stem + "_converted.txt"
    )

    try:
        converted = convert_text(
            args.input.read_text(encoding="utf-8", errors="replace")
        )
        output_path.write_text(
            converted, encoding="utf-8", newline="\r\n"
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    print(f"Converted: {args.input}")
    print(f"Saved:     {output_path}")

    grid_section = converted.split("<grid>\n", 1)[1].split(
        "\n<across>", 1
    )[0]
    print(f"Grid:      {len(grid_section.splitlines())} rows")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
