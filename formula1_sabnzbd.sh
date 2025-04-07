#!/bin/bash

# Set destination dir
# plex dir for formula 1
dest_dir="/media/pool.media/formula1"
# poster dir where templates for episode poster resides. this must be accessible from 
# sabnzbd container if you are running sabnzbd in docker
poster_dir="/config/scripts/formula_posters"

# set some variables we need
src_dir="$1"
job_name="$3"
sab_file=$(find "$src_dir" -type f | sort -n | tail -1)
extension="${sab_file##*.}"
new_filename="${job_name}.${extension}"

# filter files that we know we don't want and abort script if unwanted file is downloaded
# this is case senstive and keeps the script from breaking if file name does not match exactly
# this is similar to ACCEPT in sabnzbd RSS filter, but the regex in sab is case insensitive 
wanted=$(echo "${new_filename}" | grep -E "FP1|FP2|FP3|Sprint|Qualifying|Race" | grep -E "SKY|F1TV|F1LIVE")
if [ -z "${wanted}" ]; then
  echo "Filename does not match wanted criteria ... aborting"
  rm -rf "${src_dir}"
  exit 1
fi

# Type to Episode Number Loookup Table. This keeps things in order even with sprint race weekends
declare -A type_episode_arry
type_episode_arry["\.FP1"]="01"
type_episode_arry["\.Sprint.Qualifying"]="02"
type_episode_arry["\.Pre-Sprint.Show"]="03"
type_episode_arry["\.Sprint"]="04"
type_episode_arry["\.Post-Sprint.Show"]="05"
type_episode_arry["\.FP2"]="06"
type_episode_arry["\.FP3"]="07"
type_episode_arry["\.Pre-Qualifying.Show"]="08"
type_episode_arry["\.Qualifying"]="09"
type_episode_arry["\.Post-Qualifying.Show"]="10"
type_episode_arry["\.Pre-Race.Show"]="11"
type_episode_arry["\.Race"]="12"
type_episode_arry["\.Post-Race.Show"]="13"
type_episode_arry["\.Post-Race.Press.Conference"]="14"

# extract info we need to rename for plex
year=$(echo "${new_filename}" | cut -d. -f2)
round=$(echo "${new_filename}" | cut -d. -f3)
location=$(echo "${new_filename}" | cut -d. -f4)
type=$(echo "${new_filename}" | sed 's/\(.F1.*\|.SKY.*\)//' | cut -d. -f5- )
season=$(echo "${round}" | sed 's/Round//') 
episode="${type_episode_arry["$type"]}"

# Define new directory and filename
plex_dir="${dest_dir}/F1 ${year}/Season ${season}"
plex_name="S${season}E${episode} - ${location} Grand Prix - ${type}"
plex_filename="${plex_name}.${extension}"
plex_poster="${plex_name}.png"

# move files to plex library. This will download SKY network feeds, and 
# replace with F1[TV|LIVE] when it becomes available.
mkdir -p "${plex_dir}"

if [[ "${new_filename}" == *".SKY"* ]]; then
  if [ ! -f "${plex_dir}/${plex_filename}" ]; then
    echo "Feed is SKY and file does not exist ... copying"
    mv "${sab_file}" "${plex_dir}/${plex_filename}"
    cp "/config/scripts/formula_posters/${episode}.png" "${plex_dir}/${plex_poster}"
  fi
  if [ -f "${plex_dir}/${plex_filename}" ]; then
    echo "Feed is SKY and file already exists ... aborting"
  fi
fi

if [[ "${new_filename}" == *".F1TV"* || "${new_filename}" == *".F1LIVE"* ]]; then
  echo "Feed is F1[TV|LIVE] ... copying"	
  mv "${sab_file}" "${plex_dir}/${plex_filename}"
  cp "${poster_dir}/${episode}.png" "${plex_dir}/${plex_poster}"
fi

# cleanup files from sabnzbd
rm -rf "${src_dir}"
chmod 774 "${plex_dir}/${plex_filename}"
