#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import shutil
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR / "config"
DEFAULT_CONFIG_PATH = CONFIG_DIR / "formula1_config.toml"

MEDIA_EXTENSIONS = {".mkv", ".mp4", ".avi", ".ts", ".m4v"}
ALLOWED_RESOLUTIONS = {"720p", "1080p", "2160p"}
SESSION_ORDER = ["FP1", "FP2", "FP3", "Sprint.Qualifying", "Sprint", "Qualifying", "Race"]
SESSION_TO_EPISODE = {
    "FP1": "01",
    "FP2": "02",
    "FP3": "03",
    "Sprint.Qualifying": "04",
    "Sprint": "05",
    "Qualifying": "06",
    "Race": "07",
}
TVDB_EPISODE_RE = re.compile(r"(S(?P<year>\d{4})E(?P<episode>\d{2,3}))", re.IGNORECASE)
PART_RE = re.compile(r"\.part\.\d+\b", re.IGNORECASE)


def load_runtime_config(config_path: Optional[Path] = None) -> Dict[str, object]:
    config_path = config_path or DEFAULT_CONFIG_PATH
    with config_path.open("rb") as handle:
        config = tomllib.load(handle)

    preferred_resolution = str(config.get("preferred_resolution", "1080p")).lower()
    if preferred_resolution not in ALLOWED_RESOLUTIONS:
        raise ValueError(
            f"preferred_resolution must be one of {sorted(ALLOWED_RESOLUTIONS)}; got {preferred_resolution!r}"
        )

    dest_dir = Path(config["dest_dir"])
    config["dest_dir"] = dest_dir
    config["poster_episode_dir"] = Path(config["poster_episode_dir"])
    config["poster_season_dir"] = Path(config["poster_season_dir"])
    config["state_dir"] = dest_dir / config.get("state_dirname", ".metadata")
    config["preferred_resolution"] = preferred_resolution

    schedule_file = Path(config.get("schedule_file", "round_schedules.json"))
    if not schedule_file.is_absolute():
        schedule_file = config_path.parent / schedule_file
    config["schedule_file"] = schedule_file
    config["round_schedules"] = json.loads(schedule_file.read_text())
    return config


CONFIG = load_runtime_config()
PREFERRED_RESOLUTION = str(CONFIG["preferred_resolution"]).lower()
DEST_DIR = Path(CONFIG["dest_dir"])
POSTER_EPISODE = Path(CONFIG["poster_episode_dir"])
POSTER_SEASON = Path(CONFIG["poster_season_dir"])
STATE_DIR = Path(CONFIG["state_dir"])
DELETE_REJECTED_FILES = bool(CONFIG.get("delete_rejected_files", True))
EXPECTED_RELEASE_GROUP = str(CONFIG["release_group"]).lower()
ROUND_SCHEDULES = dict(CONFIG["round_schedules"])


@dataclass
class ParsedRelease:
    path: Path
    year: str
    season: str
    location: str
    key: str
    episode: str
    tvdb_episode_code: str
    tvdb_title: str
    release_group: str
    resolution: str

    @property
    def extension(self) -> str:
        return self.path.suffix.lstrip(".")

    @property
    def plex_name(self) -> str:
        return f"S{self.season}E{self.episode} - {self.location} Grand Prix - {self.key}"

    @property
    def plex_filename(self) -> str:
        return f"{self.plex_name}.{self.extension}"


def log(message: str) -> None:
    print(message, flush=True)


def media_files_in(directory: Path) -> list[Path]:
    files = [path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS]
    return sorted(files)


def extract_release_group(filename: str) -> str:
    stem = Path(filename).stem
    normalized = stem.replace(".", "-")
    if "-" in normalized:
        return normalized.rsplit("-", 1)[-1]
    return "UNKNOWN"


def extract_resolution(tokens: Iterable[str]) -> str:
    for token in tokens:
        lower = token.lower()
        if lower in ALLOWED_RESOLUTIONS:
            return lower
    return PREFERRED_RESOLUTION


def has_unsupported_resolution(tokens: Iterable[str]) -> bool:
    for token in tokens:
        lower = token.lower()
        if re.fullmatch(r"\d{3,4}p", lower) and lower not in ALLOWED_RESOLUTIONS:
            return True
    return False


def lookup_tvdb_episode(year: str, episode_code: str) -> Optional[Dict[str, str]]:
    season_data = ROUND_SCHEDULES.get(year, {})
    episode_lookup = season_data.get("episode_lookup", {})
    return episode_lookup.get(episode_code)


def expected_sessions(year: str, season: str) -> list[str]:
    season_entry = ROUND_SCHEDULES.get(year, {}).get("seasons", {}).get(season, {})
    return season_entry.get("expected_core_sessions", SESSION_ORDER)


def parse_release(path: Path) -> Optional[ParsedRelease]:
    stem = path.stem
    if PART_RE.search(stem):
        return None

    parts = stem.split(".")
    if has_unsupported_resolution(parts):
        return None

    release_group = extract_release_group(path.name).lower()
    if release_group != EXPECTED_RELEASE_GROUP:
        return None

    match = TVDB_EPISODE_RE.search(stem)
    if not match:
        return None

    year = match.group("year")
    episode_code = match.group(1).upper()
    looked_up = lookup_tvdb_episode(year, episode_code)
    if not looked_up:
        return None

    resolution = extract_resolution(parts)
    return ParsedRelease(
        path=path,
        year=year,
        season=looked_up["season"],
        location=looked_up["location"],
        key=looked_up["key"],
        episode=looked_up["episode"],
        tvdb_episode_code=episode_code,
        tvdb_title=looked_up["title"],
        release_group=release_group,
        resolution=resolution,
    )


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
        episode = SESSION_TO_EPISODE[session]
        for media_path in season_dir.glob(f"S{season}E{episode} - *"):
            if media_path.suffix.lower() in MEDIA_EXTENSIONS:
                present[session] = media_path.name
                break

    expected_core = expected_sessions(year, season)
    state.update(
        {
            "year": year,
            "season": season,
            "location": location,
            "expected_core_sessions": expected_core,
            "present_sessions": [session for session in SESSION_ORDER if session in present],
            "present_core_sessions": [session for session in expected_core if session in present],
            "missing_core_sessions": [session for session in expected_core if session not in present],
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

    existing_preferred = bool(existing_meta.get("preferred_resolution"))
    candidate_preferred = candidate.resolution == PREFERRED_RESOLUTION
    if candidate_preferred and not existing_preferred:
        return True
    if existing_preferred and not candidate_preferred:
        return False

    if candidate.path.stat().st_size > int(existing_meta.get("size", 0)):
        return True
    return False


def import_release(parsed: ParsedRelease) -> tuple[bool, str]:
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
            f"Keeping existing {existing_path.name}; incoming {parsed.release_group} "
            f"at {parsed.resolution} is not preferred over the current file."
        )

    if existing_path:
        log(f"Replacing {existing_path.name} with {parsed.release_group} {parsed.tvdb_episode_code} at {parsed.resolution}")
        existing_path.unlink()
        if existing_key != parsed.plex_filename:
            files_meta.pop(existing_key, None)
    else:
        log(f"Importing {target_path.name} from {parsed.release_group} {parsed.tvdb_episode_code}")

    shutil.move(str(parsed.path), target_path)
    target_path.chmod(0o644)
    copy_posters(parsed, season_dir)

    files_meta[parsed.plex_filename] = {
        "release_group": parsed.release_group,
        "resolution": parsed.resolution,
        "preferred_resolution": parsed.resolution == PREFERRED_RESOLUTION,
        "tvdb_episode_code": parsed.tvdb_episode_code,
        "tvdb_title": parsed.tvdb_title,
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
            reject_file(media_file, "No supported TVDB-numbered Formula 1 pattern matched")
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
