#!/usr/bin/env python3
"""Refresh Psion Sidecar's software indexes from Psion Community's public API.

The full API response is retained in software_index.json because Sidecar uses
its versions, variants, reference URLs, filenames and sizes to render details
and resolve downloads. The platform indexes are derived views used for search.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

API_URL = "https://software.psion.community/api/v1/programs/"
FULL_FILENAME = "software_index.json"
PLATFORM_FILENAMES = {
    "epoc16": "epoc16_index.json",
    "epoc32": "epoc32_index.json",
}
COMPACT_FIELDS = ("id", "name", "platforms", "tags", "runtimes", "kinds")
REQUIRED_FIELDS = ("id", "name", "versions", "tags", "runtimes", "kinds", "platforms")


class IndexError(ValueError):
    """Raised when upstream data is not safe to publish as Sidecar indexes."""


def validate_catalogue(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, list) or not data:
        raise IndexError("API response must be a non-empty JSON array of programs.")

    seen_ids: set[str] = set()
    for position, program in enumerate(data):
        if not isinstance(program, dict):
            raise IndexError(f"Record {position} is not a JSON object.")
        missing = [key for key in REQUIRED_FIELDS if key not in program]
        if missing:
            raise IndexError(
                f"Record {position} is missing required field(s): {', '.join(missing)}."
            )
        program_id = program["id"]
        if not isinstance(program_id, str) or not program_id.strip():
            raise IndexError(f"Record {position} has an empty or invalid id.")
        if program_id in seen_ids:
            raise IndexError(f"Duplicate program id: {program_id}")
        seen_ids.add(program_id)
        if not isinstance(program["name"], str):
            raise IndexError(f"Program {program_id} has a non-string name.")
        if not isinstance(program["platforms"], list) or not all(
            isinstance(platform, str) for platform in program["platforms"]
        ):
            raise IndexError(f"Program {program_id} has invalid platforms.")
        for field in ("versions", "tags", "runtimes", "kinds"):
            if not isinstance(program[field], list):
                raise IndexError(f"Program {program_id} has invalid {field}: expected an array.")

    for platform in PLATFORM_FILENAMES:
        if not any(platform in program["platforms"] for program in data):
            raise IndexError(f"No records found for expected platform {platform!r}.")
    return data


def build_indexes(data: Any) -> dict[str, list[dict[str, Any]]]:
    """Return all three indexes; retain every full upstream record unchanged."""
    programs = validate_catalogue(data)
    result: dict[str, list[dict[str, Any]]] = {FULL_FILENAME: programs}

    for platform, filename in PLATFORM_FILENAMES.items():
        compact = [
            {field: program.get(field, []) for field in COMPACT_FIELDS}
            for program in programs
            if platform in program["platforms"]
        ]
        compact.sort(key=lambda program: program["name"].lower())
        result[filename] = compact

    # Cross-check that compact indexes are lossless for the fields Sidecar uses
    # to find a program, and that no program has been duplicated within an index.
    source_by_id = {program["id"]: program for program in programs}
    for filename in PLATFORM_FILENAMES.values():
        ids: set[str] = set()
        for item in result[filename]:
            if item["id"] in ids:
                raise IndexError(f"Duplicate id {item['id']} in {filename}.")
            ids.add(item["id"])
            source = source_by_id[item["id"]]
            for field in COMPACT_FIELDS:
                if item[field] != source.get(field, []):
                    raise IndexError(
                        f"{filename} changed {field!r} for program {item['id']}."
                    )
    return result


def fetch_catalogue(url: str, timeout: float) -> list[dict[str, Any]]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Psion-Sidecar-index-updater/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"API returned HTTP {response.status}.")
        payload = response.read()
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IndexError(f"API response was not valid UTF-8 JSON: {exc}") from exc
    return validate_catalogue(data)


def write_indexes(indexes: dict[str, list[dict[str, Any]]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    staged: list[tuple[Path, Path]] = []
    try:
        # Stage and flush every file before replacing any existing index.
        for filename, records in indexes.items():
            fd, temp_name = tempfile.mkstemp(
                prefix=f".{filename}.", suffix=".tmp", dir=output_dir
            )
            temp_path = Path(temp_name)
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(records, handle, ensure_ascii=False, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            staged.append((temp_path, output_dir / filename))
        for temp_path, target_path in staged:
            os.replace(temp_path, target_path)
    finally:
        for temp_path, _target_path in staged:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh Sidecar's full, EPOC16 and EPOC32 software indexes."
    )
    parser.add_argument("--url", default=API_URL, help="Upstream programs API URL.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory for the three output JSON files (default: script directory).",
    )
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout in seconds.")
    args = parser.parse_args(argv)

    try:
        programs = fetch_catalogue(args.url, args.timeout)
        indexes = build_indexes(programs)
        write_indexes(indexes, args.output_dir)
    except (OSError, RuntimeError, IndexError, ValueError) as exc:
        print(f"ERROR: indexes were not updated: {exc}", file=sys.stderr)
        return 1

    print(f"Source: {args.url}")
    print(f"Output directory: {args.output_dir.resolve()}")
    print(f"Total programs: {len(indexes[FULL_FILENAME]):,}")
    for platform, filename in PLATFORM_FILENAMES.items():
        path = args.output_dir / filename
        print(f"{platform.upper()}: {len(indexes[filename]):,} programs ({path.stat().st_size:,} bytes)")
    print(f"Full catalogue: {(args.output_dir / FULL_FILENAME).stat().st_size:,} bytes")
    print("Validation passed; all three indexes updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
