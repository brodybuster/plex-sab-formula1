#!/bin/bash
set -euo pipefail
IFS=$'
	'

# Thanks to https://gist.github.com/scottrobertson for some debugging help

# NZB RSS Feed Keywords: formula1 2025

# sabnzbd RSS Filters:
# 0 : Requires : MWR
# 1 : Reject : re: proper|notebook|multi|round00
# 2 : Requires : re: F1TV|SKY
# 3 : Requires : re: FP1|FP2|FP3|Sprint|Qualifying|Race
# 4 : *

# set to SKY or F1LIVE
PREFERRED_FEED="F1LIVE"

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

parse_release_metadata() {
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
  IFS='.' read -r -a parts_lower <<< "$(printf '%s' "${stem}" | tr '[:upper:]' '[:lower:]')"
  preferred_feed_lower=$(printf '%s' "${PREFERRED_FEED}" | tr '[:upper:]' '[:lower:]')

  # Expected pattern:
  # <series>.<year>.Round<nn>.<location...>.<event...>.<network>.WEB...
  if [[ ${#parts[@]} -lt 6 ]]; then
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
    NETWORK="${parts[after_event_index]}"
    PREFERRED_MATCH=0

    for ((i = after_event_index; i < ${#parts[@]}; i++)); do
      lower_feed="${parts_lower[i]}"

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
      NETWORK="${feed_parts[0]}"
    fi

    return 0
  done

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

# check to see what network feed the file is.
# if feed is preferred feed we keep it, even if it's been downloaded before.
# if feed is NOT preferred feed, then we only keep it if we don't already have a downloaded file
# the non preferred file will get overwritten if a preferred feed one becomes available
FILE_MOVED=0

if [[ "${PREFERRED_MATCH:-0}" -eq 1 ]]; then
  echo "File is Preferred Network (${PREFERRED_FEED})."
  mv "${SAB_FILE}" "${PLEX_DIR}/${PLEX_FILENAME}"
  FILE_MOVED=1
else
  if [ ! -f "${PLEX_DIR}/${PLEX_FILENAME}" ]; then
    echo "File is not Preferred Feed (${PREFERRED_FEED}) and file does not exist."
    mv "${SAB_FILE}" "${PLEX_DIR}/${PLEX_FILENAME}"
    FILE_MOVED=1
  else
    echo "File is not Preferred Feed (${PREFERRED_FEED}) and file already exists."
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
