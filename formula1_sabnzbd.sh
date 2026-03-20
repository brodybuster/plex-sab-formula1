#!/bin/bash
set -euo pipefail
IFS=$'
	'

# Thanks to https://gist.github.com/scottrobertson for some debugging help

# NZB RSS Feed Keywords:
# formula1 2026

# Recommended SABnzbd RSS Filters:
# 0 : Requires : re: MWR|BILLIE
# 1 : Reject : re: proper|notebook|multi|round00|academy|warmup|race\.one|race\.two|sprint\.race\.one|sprint\.race\.two
# 2 : Requires : re: 1080p
# 3 : Requires : re: FP1|FP2|FP3|Sprint|Qualifying|Race|Practice\.One|Practice\.Two|Practice\.Three|Grand\.Prix
# 4 : *

# Preferred feed within MWR-style releases.
# Example values: F1LIVE, SKY, F1TV
PREFERRED_FEED="F1LIVE"

# Preferred release family.
# MWR is the primary source format handled by this script.
# BILLIE is treated as a fallback source for matching core sessions.
PREFERRED_RELEASE_GROUP="MWR"

# set destination dir where to place processed files.
# should be in your plex media libray path
# must be accessible from sabnzbd container if you are running sabnzbd in docker
DEST_DIR="/media/pool.media/formula1"

# poster dir where templates for episode poster reside.
# must be accessible from sabnzbd container if you are running sabnzbd in docker
POSTER_EPISODE="/config/scripts/formula_posters/episode"
POSTER_SEASON="/config/scripts/formula_posters/season"

# set some basic variables we need from sabnzbd
SRC_DIR="$1"
JOB_NAME="$3"
mapfile -t MEDIA_FILES < <(find "$SRC_DIR" -type f \( -iname "*.mkv" -o -iname "*.mp4" -o -iname "*.avi" -o -iname "*.ts" -o -iname "*.m4v" \) | sort)

if [[ ${#MEDIA_FILES[@]} -eq 0 ]]; then
  echo "No media file found in ${SRC_DIR}"
  echo "Aborted"
  rm -rf "${SRC_DIR}"
  exit 0
fi

if [[ ${#MEDIA_FILES[@]} -gt 1 ]]; then
  echo "Multiple media files found in ${SRC_DIR}; selecting the largest."
  printf ' - %s\n' "${MEDIA_FILES[@]}"
fi

SAB_FILE=$(find "$SRC_DIR" -type f \( -iname "*.mkv" -o -iname "*.mp4" -o -iname "*.avi" -o -iname "*.ts" -o -iname "*.m4v" \) -printf '%s\t%p\n' | sort -nr | head -n 1 | cut -f2-)
EXTENSION="${SAB_FILE##*.}"
NEW_FILENAME="${JOB_NAME}.${EXTENSION}"

to_lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

extract_release_group() {
  local filename="$1"
  local stem="${filename%.*}"
  if [[ "${stem}" == *-* ]]; then
    printf '%s' "${stem##*-}"
  else
    printf '%s' "UNKNOWN"
  fi
}

# Maps BILLIE Grand Prix location names to the 2026 official round order.
# Source: https://www.formula1.com/en/racing/2026
# This cross-reference must be reviewed and updated for each new season.
lookup_round_by_location() {
  local year="$1"
  local location="$2"
  local normalized

  normalized=$(to_lower "${location}")
  normalized=$(printf '%s' "${normalized}" | tr '-' ' ')

  case "${year}:${normalized}" in
    2026:australia) printf '%s' "01" ;;
    2026:china) printf '%s' "02" ;;
    2026:japan) printf '%s' "03" ;;
    2026:miami) printf '%s' "04" ;;
    2026:canada) printf '%s' "05" ;;
    2026:monaco) printf '%s' "06" ;;
    2026:barcelona\ catalunya) printf '%s' "07" ;;
    2026:austria) printf '%s' "08" ;;
    2026:great\ britain) printf '%s' "09" ;;
    2026:belgium) printf '%s' "10" ;;
    2026:hungary) printf '%s' "11" ;;
    2026:netherlands) printf '%s' "12" ;;
    2026:italy) printf '%s' "13" ;;
    2026:spain) printf '%s' "14" ;;
    2026:azerbaijan) printf '%s' "15" ;;
    2026:singapore) printf '%s' "16" ;;
    2026:united\ states|2026:usa\ cota|2026:cota) printf '%s' "17" ;;
    2026:mexico) printf '%s' "18" ;;
    2026:brazil|2026:sao\ paulo) printf '%s' "19" ;;
    2026:las\ vegas|2026:usa\ las\ vegas) printf '%s' "20" ;;
    2026:qatar) printf '%s' "21" ;;
    2026:abu\ dhabi) printf '%s' "22" ;;
    *) return 1 ;;
  esac
}

parse_mwr_release_metadata() {
  local filename="$1"
  local stem="${filename%.*}"
  local preferred_feed_lower
  local -a parts
  local -a parts_lower
  local -a location_parts=()
  local -a feed_parts=()
  local i token remaining remaining_lower event_parts
  local after_event_index
  local lower_feed

  IFS='.' read -r -a parts <<< "${stem}"
  IFS='.' read -r -a parts_lower <<< "$(to_lower "${stem}")"
  preferred_feed_lower=$(to_lower "${PREFERRED_FEED}")

  # Expected MWR-style pattern:
  # <series>.<year>.Round<nn>.<location...>.<event...>.<feed tags...>.<tech tags...>-MWR
  if [[ ${#parts[@]} -lt 6 ]]; then
    return 1
  fi

  if [[ "$(to_lower "${parts[2]}")" != round* ]]; then
    return 1
  fi

  YEAR="${parts[1]}"
  SEASON=$(printf '%s' "${parts[2]}" | sed 's/^[Rr][Oo][Uu][Nn][Dd]//')

  for ((i = 3; i < ${#parts[@]}; i++)); do
    token="${parts[i]}"
    remaining=$(IFS='.'; echo "${parts[*]:$i}")
    remaining_lower=$(IFS='.'; echo "${parts_lower[*]:$i}")

    case "${remaining_lower}" in
      post-race.press.conference.*) KEY="Post-Race.Press.Conference"; EPISODE="14"; event_parts=4 ;;
      post-race.show.*)             KEY="Post-Race.Show"; EPISODE="13"; event_parts=3 ;;
      post-qualifying.show.*)       KEY="Post-Qualifying.Show"; EPISODE="10"; event_parts=3 ;;
      post-sprint.show.*)           KEY="Post-Sprint.Show"; EPISODE="05"; event_parts=3 ;;
      pre-qualifying.show.*)        KEY="Pre-Qualifying.Show"; EPISODE="08"; event_parts=3 ;;
      pre-sprint.show.*)            KEY="Pre-Sprint.Show"; EPISODE="03"; event_parts=3 ;;
      pre-race.show.*)              KEY="Pre-Race.Show"; EPISODE="11"; event_parts=3 ;;
      sprint.qualifying.*)          KEY="Sprint.Qualifying"; EPISODE="02"; event_parts=2 ;;
      qualifying.*)                 KEY="Qualifying"; EPISODE="09"; event_parts=1 ;;
      sprint.*)                     KEY="Sprint"; EPISODE="04"; event_parts=1 ;;
      race.*)                       KEY="Race"; EPISODE="12"; event_parts=1 ;;
      fp3.*)                        KEY="FP3"; EPISODE="07"; event_parts=1 ;;
      fp2.*)                        KEY="FP2"; EPISODE="06"; event_parts=1 ;;
      fp1.*)                        KEY="FP1"; EPISODE="01"; event_parts=1 ;;
      *)
        location_parts+=("${token}")
        continue
        ;;
    esac

    LOCATION=$(IFS=' '; echo "${location_parts[*]}")
    after_event_index=$((i + event_parts))
    # SOURCE_TAG represents the first feed/source tag after the event,
    # such as F1LIVE, SKY, or F1TV.
    SOURCE_TAG="${parts[after_event_index]}"
    PREFERRED_MATCH=0

    for ((i = after_event_index; i < ${#parts[@]}; i++)); do
      lower_feed="${parts_lower[i]}"

      # Stop scanning source tags once we reach technical release metadata.
      case "${lower_feed}" in
        web|web-dl|webrip|bluray|hdrip|dvdrip|bdrip|remux|x264|x265|h264|h265|hevc|avc|aac|ddp*|ac3|eac3|dts*|truehd|atmos|2160p|1080p|720p|576p|480p|multi|english|proper|repack|uncut)
          break
          ;;
      esac

      feed_parts+=("${parts[i]}")
      if [[ "${lower_feed}" == "${preferred_feed_lower}" ]]; then
        PREFERRED_MATCH=1
      fi
    done

    if [[ ${#feed_parts[@]} -gt 0 ]]; then
      SOURCE_TAG="${feed_parts[0]}"
    fi

    return 0
  done

  return 1
}

parse_billie_release_metadata() {
  local filename="$1"
  local stem="${filename%.*}"
  local -a parts
  local -a parts_lower
  local -a location_parts=()
  local i remaining_lower event_parts

  IFS='.' read -r -a parts <<< "${stem}"
  IFS='.' read -r -a parts_lower <<< "$(to_lower "${stem}")"

  # Expected BILLIE-style patterns:
  # Formula1.<year>.<location>.Grand.Prix.<event...>.<tech tags...>-BILLIE
  # Formula1.<year>.<location>.Grand.Prix.<tech tags...>-BILLIE  (full race)
  # Only core F1 sessions are accepted here. Academy, warmup, and split races are rejected.
  if [[ ${#parts[@]} -lt 5 ]]; then
    return 1
  fi

  if [[ "${parts_lower[0]}" != "formula1" ]]; then
    return 1
  fi

  if [[ "${parts_lower[1]}" == "academy" ]]; then
    return 1
  fi

  YEAR="${parts[1]}"

  for ((i = 2; i < ${#parts[@]}; i++)); do
    remaining_lower=$(IFS='.'; echo "${parts_lower[*]:$i}")

    case "${remaining_lower}" in
      grand.prix.sprint.qualifying.*) KEY="Sprint.Qualifying"; EPISODE="02"; event_parts=4 ;;
      grand.prix.sprint.race.one.*|grand.prix.sprint.race.two.*|grand.prix.race.one.*|grand.prix.race.two.*|weekend.warmup.*)
        return 1
        ;;
      grand.prix.2160p.*|grand.prix.1080p.*|grand.prix.720p.*|grand.prix.576p.*|grand.prix.480p.*)
        KEY="Race"; EPISODE="12"; event_parts=2
        ;;
      grand.prix.sprint.race.*)       KEY="Sprint"; EPISODE="04"; event_parts=4 ;;
      grand.prix.qualifying.*)        KEY="Qualifying"; EPISODE="09"; event_parts=3 ;;
      grand.prix.race.*)              KEY="Race"; EPISODE="12"; event_parts=3 ;;
      practice.one.*)                 KEY="FP1"; EPISODE="01"; event_parts=2 ;;
      practice.two.*)                 KEY="FP2"; EPISODE="06"; event_parts=2 ;;
      practice.three.*)               KEY="FP3"; EPISODE="07"; event_parts=2 ;;
      *)
        location_parts+=("${parts[i]}")
        continue
        ;;
    esac

    LOCATION=$(IFS=' '; echo "${location_parts[*]}")
    SEASON=$(lookup_round_by_location "${YEAR}" "${LOCATION}") || return 1
    SOURCE_TAG="BILLIE"
    PREFERRED_MATCH=0
    return 0
  done

  return 1
}

parse_release_metadata() {
  local filename="$1"

  RELEASE_GROUP=$(extract_release_group "${filename}")

  if parse_mwr_release_metadata "${filename}"; then
    return 0
  fi

  if [[ "$(to_lower "${RELEASE_GROUP}")" == "billie" ]] && parse_billie_release_metadata "${filename}"; then
    return 0
  fi

  return 1
}

if ! parse_release_metadata "${NEW_FILENAME}"; then
  echo "Filename does not contain wanted episode criteria"
  echo "Aborted"
  rm -rf "${SRC_DIR}"
  exit 0
fi

# define new directory and filename for plex
PLEX_DIR="${DEST_DIR}/F1 ${YEAR}/Season ${SEASON}"
PLEX_NAME="S${SEASON}E${EPISODE} - ${LOCATION} Grand Prix - ${KEY}"
PLEX_FILENAME="${PLEX_NAME}.${EXTENSION}"
PLEX_POSTER="${PLEX_NAME}.png"

# create needed directories
mkdir -p "${PLEX_DIR}"

# Replacement rules:
# 1. If the target file does not exist yet, save either release family.
# 2. BILLIE is fallback-only and never replaces an existing file.
# 3. MWR can replace an existing file only when it matches PREFERRED_FEED.
FILE_MOVED=0

if [[ ! -f "${PLEX_DIR}/${PLEX_FILENAME}" ]]; then
  echo "File does not already exist. Saving ${RELEASE_GROUP} release."
  mv "${SAB_FILE}" "${PLEX_DIR}/${PLEX_FILENAME}"
  FILE_MOVED=1
else
  if [[ "$(to_lower "${RELEASE_GROUP}")" != "$(to_lower "${PREFERRED_RELEASE_GROUP}")" ]]; then
    echo "Fallback release group (${RELEASE_GROUP}) found, but target file already exists."
    echo "Skipped"
    rm -rf "${SRC_DIR}"
    exit 0
  fi

  if [[ "${PREFERRED_MATCH:-0}" -eq 1 ]]; then
    echo "Preferred ${RELEASE_GROUP} feed detected (${PREFERRED_FEED}). Replacing existing file."
    mv "${SAB_FILE}" "${PLEX_DIR}/${PLEX_FILENAME}"
    FILE_MOVED=1
  else
    echo "Non-preferred ${RELEASE_GROUP} release found and target file already exists."
    echo "Skipped"
    rm -rf "${SRC_DIR}"
    exit 0
  fi
fi

# remove sabnzbd files that are left over
echo "Cleaning up sabnzbd files"
rm -rf "${SRC_DIR}"

# set user friendly permissions
echo "Setting permissions for ${PLEX_DIR}/${PLEX_FILENAME}"
chmod 755 "${PLEX_DIR}/${PLEX_FILENAME}"

# Episode poster copy (non-fatal)
{
  EPISODE_POSTER_SOURCE="${POSTER_EPISODE}/${EPISODE}.png"
  EPISODE_POSTER_DEST="${PLEX_DIR}/${PLEX_POSTER}"
  if [[ -f "${EPISODE_POSTER_SOURCE}" ]]; then
    echo "Copying episode poster to ${EPISODE_POSTER_DEST}"
    cp "${EPISODE_POSTER_SOURCE}" "${EPISODE_POSTER_DEST}"
  else
    echo "Warning: Episode poster not found for ${EPISODE} (${EPISODE_POSTER_SOURCE})"
  fi
} || {
  echo "Episode poster copy step failed (ignored)."
}

# Season poster copy (non-fatal)
{
  SEASON_POSTER_SOURCE="${POSTER_SEASON}/${SEASON}.png"
  SEASON_POSTER_DEST="${PLEX_DIR}/season${SEASON}.png"
  if [[ -f "${SEASON_POSTER_SOURCE}" ]]; then
    echo "Copying season poster to ${SEASON_POSTER_DEST}"
    cp "${SEASON_POSTER_SOURCE}" "${SEASON_POSTER_DEST}"
  else
    echo "Warning: Season poster not found for ${SEASON} (${SEASON_POSTER_SOURCE})"
  fi
} || {
  echo "Season poster copy step failed (ignored)."
}

echo "Done"

exit 0
