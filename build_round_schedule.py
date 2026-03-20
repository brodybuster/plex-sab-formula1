#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import tomllib
import unicodedata
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = SCRIPT_DIR / "config" / "formula1_config.toml"
DEFAULT_OUTPUT_PATH = SCRIPT_DIR / "config" / "round_schedules.json"

MONTH_PATTERN = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)"
DATE_RE = re.compile(rf"^{MONTH_PATTERN}\s+\d{{1,2}}(?:\s*-\s*(?:{MONTH_PATTERN}\s+)?\d{{1,2}})?$")

TITLE_RULES = [
    ("australian gp", "Australia", ["Melbourne"]),
    ("chinese gp", "China", ["Shanghai"]),
    ("japanese gp", "Japan", ["Suzuka"]),
    ("bahrain gp", "Bahrain", ["Sakhir"]),
    ("saudi arabian gp", "Saudi Arabia", ["Jeddah"]),
    ("miami gp", "Miami", ["USA Miami"]),
    ("canadian gp", "Canada", ["Montreal"]),
    ("monaco gp", "Monaco", []),
    ("barcelona-catalunya gp", "Barcelona Catalunya", ["Barcelona", "Spain Barcelona"]),
    ("austrian gp", "Austria", ["Spielberg"]),
    ("british gp", "Great Britain", ["Silverstone"]),
    ("belgian gp", "Belgium", ["Spa", "Spa Francorchamps"]),
    ("hungarian gp", "Hungary", ["Budapest"]),
    ("dutch gp", "Netherlands", ["Zandvoort"]),
    ("italian gp", "Italy", ["Monza"]),
    ("spanish gp", "Spain", ["Madrid"]),
    ("azerbaijan gp", "Azerbaijan", ["Baku"]),
    ("singapore gp", "Singapore", []),
    ("united states gp", "United States", ["USA COTA", "COTA", "Austin"]),
    ("mexico city gp", "Mexico", ["Mexico City"]),
    ("sao paulo gp", "Brazil", ["Sao Paulo", "Interlagos"]),
    ("são paulo gp", "Brazil", ["Sao Paulo", "Interlagos"]),
    ("las vegas gp", "Las Vegas", ["USA Las Vegas"]),
    ("qatar gp", "Qatar", ["Lusail"]),
    ("abu dhabi gp", "Abu Dhabi", ["Yas Marina"]),
]


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
        description="Build or update round_schedules.json from a season text file or the configured ESPN calendar."
    )
    parser.add_argument("--year", required=True, help="Season year, for example 2027")
    parser.add_argument(
        "--input",
        type=Path,
        help="Optional path to a season definition text file",
    )
    parser.add_argument(
        "--url",
        help="Optional calendar URL. Defaults to calendar_url in config/formula1_config.toml",
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        type=Path,
        help="Path to the TOML config file",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        type=Path,
        help="Path to the round_schedules.json file to update",
    )
    return parser.parse_args()


def load_config(path: Path) -> Dict[str, object]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def parse_canceled(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in {"canceled", "cancelled", "true", "yes", "y", "1"}


def parse_line(line: str, line_number: int) -> Dict[str, object]:
    parts = [part.strip() for part in line.split("|")]
    if len(parts) < 3:
        raise ValueError(f"Line {line_number}: expected 'round | location | alias1, alias2[, canceled]'")

    round_number = parts[0].zfill(2)
    location = parts[1]
    aliases_field = parts[2]
    canceled = False

    if len(parts) >= 4:
        third = parts[2].strip().lower()
        if third in {"sprint", "race", "standard", "true", "false", "yes", "no", "y", "n", "1", "0"}:
            aliases_field = parts[3]
            if len(parts) >= 5:
                canceled = parse_canceled(parts[4])
        else:
            canceled = parse_canceled(parts[3])

    aliases = [alias.strip() for alias in aliases_field.split(",") if alias.strip()]

    if not aliases:
        aliases = [location]

    if location not in aliases:
        aliases.insert(0, location)

    return {
        "round": round_number,
        "location": location,
        "aliases": aliases,
        "canceled": canceled,
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


def fetch_html(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(request) as response:
        return response.read().decode("utf-8", errors="replace")


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.split()).strip()


def is_date_chunk(chunk: str) -> bool:
    return bool(DATE_RE.match(chunk))


def is_race_title(chunk: str, year: str) -> bool:
    lower = chunk.lower()
    if year in chunk or "calendar" in lower:
        return False
    return " gp" in lower or lower.endswith("gp")


def infer_location(title: str) -> Dict[str, object]:
    normalized = normalize_text(title).lower()
    for pattern, canonical, aliases in TITLE_RULES:
        if pattern in normalized:
            all_aliases = [canonical] + aliases
            deduped = []
            for alias in all_aliases:
                if alias not in deduped:
                    deduped.append(alias)
            return {
                "location": canonical,
                "aliases": deduped,
            }

    simplified = re.sub(r".*?([A-Za-z][A-Za-z\s-]+)\s+GP$", r"\1", normalize_text(title)).strip()
    return {
        "location": simplified or normalize_text(title),
        "aliases": [simplified or normalize_text(title)],
    }


def scrape_espn_schedule(year: str, url: str) -> List[Dict[str, object]]:
    html = fetch_html(url)
    parser = TextExtractor()
    parser.feed(html)
    chunks = parser.chunks

    entries: List[Dict[str, object]] = []
    index = 0
    while index < len(chunks):
        chunk = chunks[index]
        if not is_date_chunk(chunk):
            index += 1
            continue

        next_date_index = len(chunks)
        for probe in range(index + 1, len(chunks)):
            if is_date_chunk(chunks[probe]):
                next_date_index = probe
                break

        title = None
        venue = None
        canceled = False

        for probe in range(index + 1, next_date_index):
            candidate = chunks[probe]
            if candidate == "Canceled":
                canceled = True
                continue
            if title is None and is_race_title(candidate, year):
                title = candidate
                continue
            if title is not None and venue is None:
                lower = candidate.lower()
                if candidate == "Canceled":
                    canceled = True
                    continue
                if is_date_chunk(candidate) or "apple tv" in lower:
                    continue
                if re.match(r"^[A-Z]\.\s", candidate):
                    continue
                venue = candidate
                break

        if title:
            location_info = infer_location(title)
            if venue:
                venue_alias = normalize_text(venue)
                if venue_alias and venue_alias not in location_info["aliases"]:
                    location_info["aliases"].append(venue_alias)
            entries.append(
                {
                    "round": str(len(entries) + 1).zfill(2),
                    "location": location_info["location"],
                    "aliases": location_info["aliases"],
                    "canceled": canceled,
                }
            )

        index = next_date_index

    return entries


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    entries = load_input(args.input) if args.input else scrape_espn_schedule(args.year, args.url or str(config["calendar_url"]))
    schedule = load_schedule(args.output)

    schedule[args.year] = {
        entry["round"]: {
            "location": entry["location"],
            "aliases": entry["aliases"],
            "canceled": entry["canceled"],
        }
        for entry in entries
    }

    args.output.write_text(json.dumps(schedule, indent=2, sort_keys=True) + "\n")
    print(f"Updated {args.output} with {len(entries)} rounds for {args.year}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
