#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import shutil
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR / "config"
DEFAULT_CONFIG_PATH = CONFIG_DIR / "formula1_config.toml"

MEDIA_EXTENSIONS = {".mkv", ".mp4", ".avi", ".ts", ".m4v"}
TECH_TOKENS = {
    "web",
    "web-dl",
    "webrip",
    "bluray",
    "hdrip",
    "dvdrip",
    "bdrip",
    "remux",
    "x264",
    "x265",
    "h264",
    "h265",
    "hevc",
    "avc",
    "aac",
    "ac3",
    "eac3",
    "truehd",
    "atmos",
    "multi",
    "english",
    "proper",
    "repack",
    "uncut",
}
TECH_PREFIXES = ("ddp", "dts")
SESSION_ORDER = [
    "FP1",
    "Sprint.Qualifying",
    "Pre-Sprint.Show",
    "Sprint",
    "Post-Sprint.Show",
    "FP2",
    "FP3",
    "Pre-Qualifying.Show",
    "Qualifying",
    "Post-Qualifying.Show",
    "Pre-Race.Show",
    "Race",
    "Post-Race.Show",
    "Post-Race.Press.Conference",
]

SESSION_TO_EPISODE = {
    "FP1": "01",
    "Sprint.Qualifying": "02",
    "Pre-Sprint.Show": "03",
    "Sprint": "04",
    "Post-Sprint.Show": "05",
    "FP2": "06",
    "FP3": "07",
    "Pre-Qualifying.Show": "08",
    "Qualifying": "09",
    "Post-Qualifying.Show": "10",
    "Pre-Race.Show": "11",
    "Race": "12",
    "Post-Race.Show": "13",
    "Post-Race.Press.Conference": "14",
}

CORE_SESSIONS = {"FP1", "FP2", "FP3", "Sprint.Qualifying", "Sprint", "Qualifying", "Race"}
BONUS_SESSIONS = {
    "Pre-Sprint.Show",
    "Post-Sprint.Show",
    "Pre-Qualifying.Show",
    "Post-Qualifying.Show",
    "Pre-Race.Show",
    "Post-Race.Show",
    "Post-Race.Press.Conference",
}


def load_runtime_config(config_path: Optional[Path] = None) -> Dict[str, object]:
    config_path = config_path or DEFAULT_CONFIG_PATH
    with config_path.open("rb") as handle:
        config = tomllib.load(handle)

    dest_dir = Path(config["dest_dir"])
    config["dest_dir"] = dest_dir
    config["poster_episode_dir"] = Path(config["poster_episode_dir"])
    config["poster_season_dir"] = Path(config["poster_season_dir"])
    config["state_dir"] = dest_dir / config.get("state_dirname", ".metadata")

    schedule_file = Path(config.get("schedule_file", "round_schedules.json"))
    if not schedule_file.is_absolute():
        schedule_file = config_path.parent / schedule_file
    config["schedule_file"] = schedule_file
    config["round_schedules"] = json.loads(schedule_file.read_text())
    return config


CONFIG = load_runtime_config()
PREFERRED_FEED = str(CONFIG["preferred_feed"])
RELEASE_FAMILY_RANK = dict(CONFIG["release_family_rank"])
SOURCE_TAG_RANK = dict(CONFIG["source_tag_rank"])
RESOLUTION_RANK = dict(CONFIG["resolution_rank"])
DEFAULT_RESOLUTION = str(CONFIG["default_resolution"]).lower()
DEST_DIR = Path(CONFIG["dest_dir"])
POSTER_EPISODE = Path(CONFIG["poster_episode_dir"])
POSTER_SEASON = Path(CONFIG["poster_season_dir"])
STATE_DIR = Path(CONFIG["state_dir"])
INCLUDE_EXTRAS = bool(CONFIG["include_extras"])
ROUND_SCHEDULES = dict(CONFIG["round_schedules"])
DELETE_REJECTED_FILES = bool(CONFIG.get("delete_rejected_files", True))


@dataclass
class ParsedRelease:
    path: Path
    year: str
    season: str
    location: str
    key: str
    episode: str
    release_group: str
    source_tag: str
    preferred_match: bool
    resolution: Optional[str]
    ranking_score: int
    parse_source: str

    @property
    def extension(self) -> str:
        return self.path.suffix.lstrip(".")

    @property
    def plex_name(self) -> str:
        return f"S{self.season}E{self.episode} - {self.location} Grand Prix - {self.key}"

    @property
    def plex_filename(self) -> str:
        return f"{self.plex_name}.{self.extension}"

    @property
    def is_core_session(self) -> bool:
        return self.key in CORE_SESSIONS

    @property
    def is_bonus_session(self) -> bool:
        return self.key in BONUS_SESSIONS


def log(message: str) -> None:
    print(message, flush=True)


def normalize_name(value: str) -> str:
    value = value.replace("-", " ").replace("_", " ").replace(".", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip().lower()


def media_files_in(directory: Path) -> list[Path]:
    files = [path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS]
    return sorted(files)


def extract_release_group(filename: str) -> str:
    stem = Path(filename).stem
    return stem.rsplit("-", 1)[-1] if "-" in stem else "UNKNOWN"


def extract_resolution(tokens: Iterable[str]) -> Optional[str]:
    for token in tokens:
        lower = token.lower()
        if lower in RESOLUTION_RANK:
            return lower
    return DEFAULT_RESOLUTION


def has_unsupported_resolution(tokens: Iterable[str]) -> bool:
    for token in tokens:
        lower = token.lower()
        if re.fullmatch(r"\d{3,4}p", lower) and lower not in RESOLUTION_RANK:
            return True
    return False


def is_tech_token(token: str) -> bool:
    lower = token.lower()
    return lower in TECH_TOKENS or lower.startswith(TECH_PREFIXES) or lower in RESOLUTION_RANK


def lookup_round_by_location(year: str, location: str) -> Optional[Tuple[str, str]]:
    schedule = ROUND_SCHEDULES.get(year, {})
    wanted = normalize_name(location)
    for season, info in schedule.items():
        aliases = [normalize_name(alias) for alias in info["aliases"]]
        if wanted in aliases:
            return season, info["location"]
    return None


def expected_sessions(year: str, season: str) -> list[str]:
    return ["FP1", "FP2", "FP3", "Sprint.Qualifying", "Sprint", "Qualifying", "Race"]


def expected_bonus_sessions(year: str, season: str) -> list[str]:
    return [
        "Pre-Sprint.Show",
        "Post-Sprint.Show",
        "Pre-Qualifying.Show",
        "Post-Qualifying.Show",
        "Pre-Race.Show",
        "Post-Race.Show",
        "Post-Race.Press.Conference",
    ]


def build_ranking_score(release_group: str, source_tag: str, resolution: Optional[str]) -> int:
    release_rank = RELEASE_FAMILY_RANK.get(release_group.upper(), 0)
    source_rank = SOURCE_TAG_RANK.get(source_tag.upper(), 0)
    resolution_rank = RESOLUTION_RANK.get((resolution or "").lower(), 0)
    preferred_bonus = 5 if source_tag.upper() == PREFERRED_FEED.upper() else 0
    return release_rank + source_rank + resolution_rank + preferred_bonus


def parse_mwr_release(path: Path) -> Optional[ParsedRelease]:
    stem = path.stem
    parts = stem.split(".")
    parts_lower = [part.lower() for part in parts]

    if len(parts) < 6 or not parts_lower[2].startswith("round"):
        return None
    if has_unsupported_resolution(parts):
        return None

    year = parts[1]
    season = re.sub(r"(?i)^round", "", parts[2]).zfill(2)
    location_parts: list[str] = []

    event_map = [
        (["post", "race", "press", "conference"], "Post-Race.Press.Conference"),
        (["post", "race", "show"], "Post-Race.Show"),
        (["post", "qualifying", "show"], "Post-Qualifying.Show"),
        (["post", "sprint", "show"], "Post-Sprint.Show"),
        (["pre", "qualifying", "show"], "Pre-Qualifying.Show"),
        (["pre", "sprint", "show"], "Pre-Sprint.Show"),
        (["pre", "race", "show"], "Pre-Race.Show"),
        (["sprint", "qualifying"], "Sprint.Qualifying"),
        (["qualifying"], "Qualifying"),
        (["sprint"], "Sprint"),
        (["race"], "Race"),
        (["fp3"], "FP3"),
        (["fp2"], "FP2"),
        (["fp1"], "FP1"),
    ]

    for index in range(3, len(parts)):
        remaining = parts_lower[index:]
        matched_key = None
        matched_len = 0
        for pattern, key in event_map:
            if remaining[: len(pattern)] == pattern:
                matched_key = key
                matched_len = len(pattern)
                break
        if not matched_key:
            location_parts.append(parts[index])
            continue

        after_event_index = index + matched_len
        if after_event_index >= len(parts):
            return None

        feed_parts: list[str] = []
        for token in parts[after_event_index:]:
            if is_tech_token(token):
                break
            feed_parts.append(token)

        source_tag = feed_parts[0] if feed_parts else parts[after_event_index]
        location = " ".join(location_parts).strip()
        resolution = extract_resolution(parts)

        return ParsedRelease(
            path=path,
            year=year,
            season=season,
            location=location,
            key=matched_key,
            episode=SESSION_TO_EPISODE[matched_key],
            release_group="MWR",
            source_tag=source_tag,
            preferred_match=source_tag.upper() == PREFERRED_FEED.upper(),
            resolution=resolution,
            ranking_score=build_ranking_score("MWR", source_tag, resolution),
            parse_source="filename",
        )

    return None


def parse_billie_release(path: Path) -> Optional[ParsedRelease]:
    stem = path.stem
    parts = stem.split(".")
    parts_lower = [part.lower() for part in parts]

    if len(parts) < 5 or parts_lower[0] != "formula1" or parts_lower[1] == "academy":
        return None
    if has_unsupported_resolution(parts):
        return None

    unsupported = {
        ("weekend", "warmup"),
        ("grand", "prix", "race", "one"),
        ("grand", "prix", "race", "two"),
        ("grand", "prix", "sprint", "race", "one"),
        ("grand", "prix", "sprint", "race", "two"),
    }

    year = parts[1]
    location_parts: list[str] = []

    for index in range(2, len(parts)):
        remaining = tuple(parts_lower[index:])
        if any(remaining[: len(pattern)] == pattern for pattern in unsupported):
            return None

        if remaining[:4] == ("grand", "prix", "sprint", "qualifying"):
            key, matched_len = "Sprint.Qualifying", 4
        elif remaining[:4] == ("grand", "prix", "sprint", "race"):
            key, matched_len = "Sprint", 4
        elif remaining[:3] == ("grand", "prix", "qualifying"):
            key, matched_len = "Qualifying", 3
        elif remaining[:3] == ("grand", "prix", "race"):
            key, matched_len = "Race", 3
        elif len(remaining) >= 3 and remaining[:2] == ("grand", "prix") and remaining[2] in RESOLUTION_RANK:
            key, matched_len = "Race", 2
        elif remaining[:2] == ("practice", "one"):
            key, matched_len = "FP1", 2
        elif remaining[:2] == ("practice", "two"):
            key, matched_len = "FP2", 2
        elif remaining[:2] == ("practice", "three"):
            key, matched_len = "FP3", 2
        else:
            location_parts.append(parts[index])
            continue

        location = " ".join(location_parts).strip()
        looked_up = lookup_round_by_location(year, location)
        if not looked_up:
            return None

        season, canonical_location = looked_up
        resolution = extract_resolution(parts)
        return ParsedRelease(
            path=path,
            year=year,
            season=season,
            location=canonical_location,
            key=key,
            episode=SESSION_TO_EPISODE[key],
            release_group="BILLIE",
            source_tag="BILLIE",
            preferred_match=False,
            resolution=resolution,
            ranking_score=build_ranking_score("BILLIE", "BILLIE", resolution),
            parse_source="filename",
        )

    return None


def parse_release(path: Path) -> Optional[ParsedRelease]:
    release_group = extract_release_group(path.name).upper()
    parsed = parse_mwr_release(path)
    if parsed:
        return parsed
    if release_group == "BILLIE":
        return parse_billie_release(path)
    return None


def state_file_path(year: str, season: str) -> Path:
    return STATE_DIR / year / f"season_{season}.json"


def load_state(year: str, season: str) -> dict:
    path = state_file_path(year, season)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_state(year: str, season: str, data: dict) -> None:
    path = state_file_path(year, season)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def build_manifest(year: str, season: str, location: str, season_dir: Path) -> dict:
    state = load_state(year, season)
    present = {}
    for session in SESSION_ORDER:
        episode = SESSION_TO_EPISODE.get(session)
        if not episode:
            continue
        for media_path in season_dir.glob(f"S{season}E{episode} - *.?*"):
            if media_path.suffix.lower() in MEDIA_EXTENSIONS:
                present[session] = media_path.name
                break

    expected_core = expected_sessions(year, season)
    expected_bonus = expected_bonus_sessions(year, season)
    state.update(
        {
            "year": year,
            "season": season,
            "location": location,
            "expected_core_sessions": expected_core,
            "expected_bonus_sessions": expected_bonus,
            "present_sessions": sorted(present.keys(), key=lambda item: SESSION_ORDER.index(item)),
            "present_core_sessions": [session for session in expected_core if session in present],
            "present_bonus_sessions": [session for session in expected_bonus if session in present],
            "missing_core_sessions": [session for session in expected_core if session not in present],
            "missing_bonus_sessions": [session for session in expected_bonus if session not in present],
            "files": present,
        }
    )
    return state


def copy_posters(parsed: ParsedRelease, season_dir: Path) -> None:
    episode_src = POSTER_EPISODE / f"{parsed.episode}.png"
    episode_dest = season_dir / f"{parsed.plex_name}.png"
    if episode_src.exists():
        log(f"Copying episode poster to {episode_dest}")
        shutil.copy2(episode_src, episode_dest)
    else:
        log(f"Warning: Episode poster not found for {parsed.episode} ({episode_src})")

    season_src = POSTER_SEASON / f"{parsed.season}.png"
    season_dest = season_dir / f"season{parsed.season}.png"
    if season_src.exists():
        log(f"Copying season poster to {season_dest}")
        shutil.copy2(season_src, season_dest)
    else:
        log(f"Warning: Season poster not found for {parsed.season} ({season_src})")


def find_existing_session_file(season_dir: Path, season: str, episode: str) -> Optional[Path]:
    matches = []
    for media_path in season_dir.glob(f"S{season}E{episode} - *"):
        if media_path.suffix.lower() in MEDIA_EXTENSIONS:
            matches.append(media_path)
    return sorted(matches)[0] if matches else None


def should_replace(existing_meta: Optional[dict], candidate: ParsedRelease) -> bool:
    if not existing_meta:
        return True
    existing_score = int(existing_meta.get("ranking_score", 0))
    if candidate.ranking_score > existing_score:
        return True
    if candidate.ranking_score == existing_score and candidate.path.stat().st_size > int(existing_meta.get("size", 0)):
        return True
    return False


def import_release(parsed: ParsedRelease) -> tuple[bool, str]:
    if not INCLUDE_EXTRAS and not parsed.is_core_session:
        return False, f"Skipping non-core session {parsed.key}"

    season_dir = DEST_DIR / f"F1 {parsed.year}" / f"Season {parsed.season}"
    season_dir.mkdir(parents=True, exist_ok=True)
    target_path = season_dir / parsed.plex_filename

    state = build_manifest(parsed.year, parsed.season, parsed.location, season_dir)
    files_meta = state.setdefault("file_details", {})
    existing_path = find_existing_session_file(season_dir, parsed.season, parsed.episode)
    existing_key = existing_path.name if existing_path else parsed.plex_filename
    existing_meta = files_meta.get(existing_key)

    if existing_path and not should_replace(existing_meta, parsed):
        return False, (
            f"Keeping existing {existing_path.name}; "
            f"incoming {parsed.release_group}/{parsed.source_tag} ranked lower or equal."
        )

    if existing_path:
        log(f"Replacing {existing_path.name} with higher-ranked {parsed.release_group}/{parsed.source_tag}")
        existing_path.unlink()
        if existing_key != parsed.plex_filename:
            files_meta.pop(existing_key, None)
    else:
        log(f"Importing {target_path.name} from {parsed.release_group}/{parsed.source_tag}")

    shutil.move(str(parsed.path), target_path)
    target_path.chmod(0o644)
    copy_posters(parsed, season_dir)

    files_meta[parsed.plex_filename] = {
        "release_group": parsed.release_group,
        "source_tag": parsed.source_tag,
        "resolution": parsed.resolution,
        "ranking_score": parsed.ranking_score,
        "size": target_path.stat().st_size,
    }
    updated_state = build_manifest(parsed.year, parsed.season, parsed.location, season_dir)
    updated_state["file_details"] = files_meta
    save_state(parsed.year, parsed.season, updated_state)
    return True, f"Saved to {target_path}"


def reject_file(path: Path, reason: str) -> None:
    log(f"Rejected {path.name}: {reason}")
    if DELETE_REJECTED_FILES and path.exists():
        path.unlink()


def cleanup_empty_directories(root: Path) -> None:
    for path in sorted((candidate for candidate in root.rglob("*") if candidate.is_dir()), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass


def main() -> int:
    if len(sys.argv) < 4:
        log("Usage: formula1_sabnzbd.py <complete_dir> <original_name> <nzb_name> ...")
        return 1

    src_dir = Path(sys.argv[1])
    media_files = media_files_in(src_dir)
    if not media_files:
        log(f"No media file found in {src_dir}")
        return 0

    if len(media_files) > 1:
        log(f"Found {len(media_files)} media files in {src_dir}; processing each candidate.")

    imported = 0
    rejected = 0
    for media_file in media_files:
        parsed = parse_release(media_file)
        if not parsed:
            rejected += 1
            reject_file(media_file, "No supported Formula 1 pattern matched")
            continue

        moved, message = import_release(parsed)
        log(message)
        if moved:
            imported += 1

    cleanup_empty_directories(src_dir)
    try:
        src_dir.rmdir()
    except OSError:
        pass

    log(f"Done: imported={imported}, rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
