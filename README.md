## Formula 1 SABnzbd Post-Processing

This repo provides a SABnzbd post-processing script for importing Formula 1 releases into a Plex TV library.

The current Python script supports:

- `playWEB` releases that use TVDB-style `S2026E##` numbering
- multi-file jobs, so one SAB download can import multiple sessions
- a generated lookup table that maps TVDB episode codes into `Season XX` race folders
- safe replacement rules based on preferred resolution, with `1080p` as the default preference

## Supported Release Logic

The script currently understands:

- `playWEB` Formula 1 releases with TVDB-style naming such as `Formula1.S2026E19.China.Race.1080p...-playWEB`

Unsupported or unwanted items are rejected by the script during post-processing. That means the script can protect your library even if a broad RSS rule lets something through.

If bandwidth matters, you should still use SAB RSS filters to prevent those releases from downloading in the first place.

## File Layout

Place these files together inside your SAB scripts path:

- `formula1_sabnzbd.py`
- `config/formula1_config.toml`
- `config/round_schedules.json`
- `formula_posters/episode/*.png`
- `formula_posters/season/*.png`

Example:

```text
/config/scripts/
├── formula1_sabnzbd.py
├── config/
│   ├── formula1_config.toml
│   └── round_schedules.json
└── formula_posters/
    ├── episode/
    │   ├── 01.png
    │   └── 12.png
    └── season/
        ├── 01.png
        └── 22.png
```

## SABnzbd Setup

1. Place `formula1_sabnzbd.py` in your SAB script directory.
2. Make it executable.
3. Place the `config/` folder next to the script.
4. Place the `formula_posters/` folder somewhere SAB can access it.
5. Update paths in `config/formula1_config.toml` to match your environment.
6. Choose `formula1_sabnzbd.py` as the post-processing script for your Formula 1 RSS feed.

If you use Docker, all of these paths must exist inside the SAB container, not just on the host.

## What The Script Imports

The script tracks core race-weekend sessions:

- `FP1`
- `FP2`
- `FP3`
- `Sprint.Qualifying`
- `Sprint`
- `Qualifying`
- `Race`

This release-group workflow does not currently target pre-show or post-show extras.

## Replacement Rules

The script prefers the configured `preferred_resolution`, which defaults to `1080p`.

Current default behavior:

- a `1080p` release is preferred over `720p` or `2160p`
- if two releases have the same preferred-status, the larger file wins

Only these explicit resolutions are accepted:

- `720p`
- `1080p`
- `2160p`

If a filename includes another explicit resolution such as `480p` or `576p`, it is rejected.

If no resolution token is present, the script treats it as `1080p` for ranking.

## Rejected Files

The script rejects unsupported or unwanted files during post-processing.

Rejected files are not imported into Plex, and they are not saved to a separate unmatched folder.

This is useful when:

- a release name does not match the supported parser
- a release uses an unsupported resolution
- a release is outside the accepted Formula 1 patterns

If you want to avoid downloading those files at all, use SAB RSS filters.

## Recommended SAB RSS Filters

Use SAB RSS filters as a coarse front-end filter, especially if you want to save bandwidth.

Example:

```text
0 : Requires : re: playWEB
1 : Reject : re: part\.1|part\.2
2 : *
```

The post-processing script remains the final safety layer, but RSS filters are the right place to reduce unwanted downloads before they consume bandwidth.

## Plex Setup

### Use Local Assets

- enable local media assets or prefer local artwork so copied posters are used
<img width="500" alt="Screenshot 2025-04-07 at 1 51 02 PM" src="https://github.com/user-attachments/assets/07fc730e-6d56-4e23-9a98-4df9623a2019" />

### Create The Library

Create a new Plex library with these recommendations:

- library type: `TV Shows`
- library path: your Formula 1 base folder, for example `/media/pool.media/formula1`
- under `Advanced`, set `Scanner` to `Plex Series Scanner`
- under `Advanced`, set `Agent` to `Personal Media Shows`
<img width="500" alt="Screenshot 2025-04-07 at 1 48 43 PM" src="https://github.com/user-attachments/assets/42296cae-ee32-4077-8497-572fca15b7db" />
<img width="500" alt="Screenshot 2025-04-07 at 1 48 54 PM" src="https://github.com/user-attachments/assets/71a7e9d6-8346-47dd-b2e0-e2a9f4721dca" />
<img width="500" alt="Screenshot 2025-04-07 at 1 49 02 PM" src="https://github.com/user-attachments/assets/75f00ee0-7ec5-4ea4-b3a2-05ac38916c21" />
<img width="500" alt="Screenshot 2025-04-07 at 1 49 15 PM" src="https://github.com/user-attachments/assets/34530ed6-aee1-4531-ae61-cd3e8c4df2a6" />
<img width="500" alt="Screenshot 2025-04-07 at 1 49 23 PM" src="https://github.com/user-attachments/assets/8b0873b7-a099-4a03-a0be-9cab98ebffab" />


This script is designed around a TV-style Plex library layout, with each race weekend stored as a `Season XX` folder and each session named like an episode.

If posters or renamed sessions do not appear immediately in Plex, refresh metadata after new imports.

## Plex Output Structure

The script expects the base destination directory to already exist.

Example:

```text
/media/pool.media/formula1
```

The script creates:

- year folders such as `F1 2026`
- season folders such as `Season 02`
- media files such as `S02E12 - China Grand Prix - Race.mkv`
- episode posters such as `S02E12 - China Grand Prix - Race.png`
- season posters such as `season02.png`

The script also writes import state outside the Plex-visible folders:

```text
/media/pool.media/formula1/.metadata/
```

Each round state file tracks:

- expected core sessions
- present sessions
- missing core sessions
- file metadata

## Posters

Poster copying is optional.

### Automatic

**Episode posters**

Place episode poster source images in `formula_posters/episode/`.

These files must be named using the episode number expected by the script.

- `formula_posters/episode/01.png`
- `formula_posters/episode/02.png`
- `formula_posters/episode/12.png`

**Season posters**

Place season poster source images in `formula_posters/season/`.

These files must be named using the season number parsed by the script. In this setup, the season number corresponds to the Formula 1 round number.

- `formula_posters/season/01.png`
- `formula_posters/season/02.png`
- `formula_posters/season/24.png`

**How the script uses them**

When a release is processed, the script parses the filename to determine the `season` and `episode` values. It then looks for matching poster files using those numbers.

Example release:

`Formula1.2025.Round24.Abu.Dhabi.Race.F1TV.WEB-DL...`

The script will look for:

- `formula_posters/episode/12.png`
- `formula_posters/season/24.png`

**Output behavior**

If matching images are found, the script copies them into the final Plex media folder automatically.

Episode posters are copied and renamed to match the final media item name.

Season posters are copied as `seasonXX.png`.

If a matching poster is missing, the media file still imports normally.

**Important**

- Filenames must match exactly.
- Use `.png` files only.
- Episode posters must use the script’s mapped episode number, not the event name.
- Season posters must use the parsed season number from the release filename.

### Manual

If you prefer not to use local poster files, you can manage artwork directly in Plex instead.

Plex documentation for local media assets:
[https://support.plex.tv/articles/200220717-local-media-assets-tv-shows/](https://support.plex.tv/articles/200220717-local-media-assets-tv-shows/)

## Updating For A New Season

The round and location mapping lives in:

- `config/round_schedules.json`

By default, `build_round_schedule.py` can scrape the calendar URL from `config/formula1_config.toml` and rebuild the round mapping automatically:

```sh
python3 build_round_schedule.py --year 2026
```

You can also build or override a season entry from a simple text file with:

```sh
python3 build_round_schedule.py --year 2027 --input season_2027.txt
```

Example input format:

```text
01 | Australia | Australia, Melbourne
02 | China     | China, Shanghai
04 | Bahrain   | Bahrain, Sakhir | canceled
```

See `season_schedule_template.txt` for the expected format.
