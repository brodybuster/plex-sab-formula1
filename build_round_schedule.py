#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import tomllib
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = SCRIPT_DIR / "config" / "formula1_config.toml"
DEFAULT_OUTPUT_PATH = SCRIPT_DIR / "config" / "round_schedules.json"
EPISODE_CODE_RE = re.compile(r"^S(?P<year>\d{4})E(?P<episode>\d{2,3})$", re.IGNORECASE)

SESSION_LABELS = {
    "practice": "FP1",
    "practice 1": "FP1",
    "practice 2": "FP2",
    "practice 3": "FP3",
    "sprint qualifying": "Sprint.Qualifying",
    "sprint race": "Sprint",
    "qualifying": "Qualifying",
    "race": "Race",
}

CORE_SESSION_ORDER = [
    "FP1",
    "FP2",
    "FP3",
    "Sprint.Qualifying",
    "Sprint",
    "Qualifying",
    "Race",
]
SESSION_TO_EPISODE = {
    "FP1": "01",
    "FP2": "02",
    "FP3": "03",
    "Sprint.Qualifying": "04",
    "Sprint": "05",
    "Qualifying": "06",
    "Race": "07",
}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.chunks: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned = " ".join(data.split())
        if cleaned:
            self.chunks.append(cleaned)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build or update round_schedules.json from a TVDB season page or a fallback text file."
    )
    parser.add_argument("--year", required=True, help="Season year, for example 2026")
    parser.add_argument("--input", type=Path, help="Optional fallback input file")
    parser.add_argument("--url", help="Optional TVDB season URL. Defaults to calendar_url in config")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, type=Path, help="Path to the TOML config file")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path, help="Path to the round_schedules.json file to update")
    return parser.parse_args()


def load_config(path: Path) -> Dict[str, object]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_schedule(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def fetch_html(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request) as response:
        return response.read().decode("utf-8", errors="replace")


def normalize_episode_code(year: str, episode_number: str) -> str:
    return "S{0}E{1}".format(year, episode_number.zfill(2))


def parse_tvdb_title(title: str) -> Optional[Dict[str, str]]:
    if "testing" in title.lower():
        return None

    match = re.match(r"^(?P<location>.+?)\s*\((?P<session>.+?)\)$", title)
    if not match:
        return None

    location = match.group("location").strip()
    session_label = match.group("session").strip().lower()
    key = SESSION_LABELS.get(session_label)
    if not key:
        return None

    return {
        "location": location,
        "key": key,
        "title": title,
    }


def scrape_tvdb_schedule(year: str, url: str) -> List[Dict[str, str]]:
    html = fetch_html(url)
    parser = TextExtractor()
    parser.feed(html)

    entries: List[Dict[str, str]] = []
    chunks = parser.chunks
    for index, chunk in enumerate(chunks):
        match = EPISODE_CODE_RE.match(chunk)
        if not match or match.group("year") != year:
            continue
        if index + 1 >= len(chunks):
            continue
        title = chunks[index + 1]
        parsed = parse_tvdb_title(title)
        if not parsed:
            continue
        entries.append(
            {
                "episode_code": normalize_episode_code(year, match.group("episode")),
                "location": parsed["location"],
                "key": parsed["key"],
                "title": parsed["title"],
            }
        )
    return entries


def parse_line(line: str, line_number: int) -> Dict[str, str]:
    parts = [part.strip() for part in line.split("|")]
    if len(parts) < 4:
        raise ValueError(f"Line {line_number}: expected 'episode_code | location | key | title'")
    return {
        "episode_code": parts[0].upper(),
        "location": parts[1],
        "key": parts[2],
        "title": parts[3],
    }


def load_input(path: Path) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        entries.append(parse_line(line, line_number))
    return entries


def build_schedule(entries: List[Dict[str, str]]) -> Dict[str, object]:
    seasons: Dict[str, Dict[str, object]] = {}
    episode_lookup: Dict[str, Dict[str, str]] = {}

    season_number = 0
    current_location = None
    for entry in entries:
        if entry["location"] != current_location:
            season_number += 1
            current_location = entry["location"]

        season = str(season_number).zfill(2)
        season_entry = seasons.setdefault(
            season,
            {
                "location": entry["location"],
                "episode_codes": [],
                "expected_core_sessions": [],
                "episodes": {},
            },
        )

        season_entry["episode_codes"].append(entry["episode_code"])
        if entry["key"] not in season_entry["expected_core_sessions"]:
            season_entry["expected_core_sessions"].append(entry["key"])
        season_entry["episodes"][entry["episode_code"]] = {
            "key": entry["key"],
            "title": entry["title"],
            "episode": SESSION_TO_EPISODE[entry["key"]],
        }

        episode_lookup[entry["episode_code"]] = {
            "season": season,
            "location": entry["location"],
            "key": entry["key"],
            "title": entry["title"],
            "episode": SESSION_TO_EPISODE[entry["key"]],
        }

    for season_entry in seasons.values():
        season_entry["expected_core_sessions"] = [
            key for key in CORE_SESSION_ORDER if key in season_entry["expected_core_sessions"]
        ]

    return {
        "seasons": seasons,
        "episode_lookup": episode_lookup,
    }


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    entries = load_input(args.input) if args.input else scrape_tvdb_schedule(args.year, args.url or str(config["calendar_url"]))
    schedule = load_schedule(args.output)
    schedule[args.year] = build_schedule(entries)
    args.output.write_text(json.dumps(schedule, indent=2, sort_keys=True) + "\n")
    print(f"Updated {args.output} with {len(entries)} episodes for {args.year}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
