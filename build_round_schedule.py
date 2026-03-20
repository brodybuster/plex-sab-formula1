#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build or update round_schedules.json from a simple season text file."
    )
    parser.add_argument("--year", required=True, help="Season year, for example 2027")
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to a season definition text file",
    )
    parser.add_argument(
        "--output",
        default=Path(__file__).resolve().parent / "config" / "round_schedules.json",
        type=Path,
        help="Path to the round_schedules.json file to update",
    )
    return parser.parse_args()


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"sprint", "true", "yes", "y", "1"}:
        return True
    if normalized in {"race", "standard", "false", "no", "n", "0"}:
        return False
    raise ValueError(f"Unsupported sprint flag '{value}'. Use sprint/true or race/false.")


def parse_line(line: str, line_number: int) -> Dict[str, object]:
    parts = [part.strip() for part in line.split("|")]
    if len(parts) < 4:
        raise ValueError(
            f"Line {line_number}: expected 'round | location | sprint_flag | alias1, alias2'"
        )

    round_number = parts[0].zfill(2)
    location = parts[1]
    sprint = parse_bool(parts[2])
    aliases = [alias.strip() for alias in parts[3].split(",") if alias.strip()]

    if not aliases:
        aliases = [location]

    if location not in aliases:
        aliases.insert(0, location)

    return {
        "round": round_number,
        "location": location,
        "aliases": aliases,
        "sprint": sprint,
    }


def load_input(path: Path) -> List[Dict[str, object]]:
    entries: List[Dict[str, object]] = []
    for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        entries.append(parse_line(line, line_number))
    return entries


def load_schedule(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def main() -> int:
    args = parse_args()
    entries = load_input(args.input)
    schedule = load_schedule(args.output)

    schedule[args.year] = {
        entry["round"]: {
            "location": entry["location"],
            "aliases": entry["aliases"],
            "sprint": entry["sprint"],
        }
        for entry in entries
    }

    args.output.write_text(json.dumps(schedule, indent=2, sort_keys=True) + "\n")
    print(f"Updated {args.output} with {len(entries)} rounds for {args.year}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
