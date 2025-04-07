#!/bin/bash

# NZB RSS Feed Keywords: formula1 2025

# sabnzb RSS Filters:
# 0 : Requires : MWR
# 1 : Reject : re: proper|notebook|multi|round00
# 2 : Requires : re: F1TV|SKY
# 3 : Requires : re: FP1|FP2|FP3|Sprint|Qualifying|Race
# 4 : *

# Set to SKY or F1TV
preferred_feed="F1TV"

# Set destination dir -> plex dir for formula 1
dest_dir="/media/pool.media/formula1"

# poster dir where templates for episode poster reside. this must be accessible from 
# sabnzbd container if you are running sabnzbd in docker
poster_dir="/config/scripts/formula_posters"

# set some basic variables we need from sabnzbd
src_dir="$1"
job_name="$3"
sab_file=$(find "$src_dir" -type f | sort -n | tail -1)
extension="${sab_file##*.}"
new_filename="${job_name}.${extension}"

# array of episodes names we are interested in, along with eposide number to assign
declare -A type_episode_arry
type_episode_arry["FP1"]="01"
type_episode_arry["Sprint.Qualifying"]="02"
type_episode_arry["Pre-Sprint.Show"]="03"
type_episode_arry["Sprint"]="04"
type_episode_arry["Post-Sprint.Show"]="05"
type_episode_arry["FP2"]="06"
type_episode_arry["FP3"]="07"
type_episode_arry["Pre-Qualifying.Show"]="08"
type_episode_arry["Qualifying"]="09"
type_episode_arry["Post-Qualifying.Show"]="10"
type_episode_arry["Pre-Race.Show"]="11"
type_episode_arry["Race"]="12"
type_episode_arry["Post-Race.Show"]="13"
type_episode_arry["Post-Race.Press.Conference"]="14"

# check to see if filename cotains any of the episodes we are interested in
found=0
for key in "${!type_episode_arry[@]}"; do
  if [ -n "$(echo "${new_filename}" | grep -Eio "\.${key}")" ]; then
    found=1
    break
 fi
done

# if filename does not contain wanted episode name, then stop and delete job
if [[ $found -eq 0 ]]; then
  echo "Filename does not contain wanted episode criteria ... aborting"
  rm -rf "${src_dir}"
  exit 1
fi

# extract info we need to rename for plex
year=$(echo "${new_filename}" | cut -d. -f2)
season=$(echo "${new_filename}" | cut -d. -f3 | sed 's/Round//')
episode="${type_episode_arry["${key}"]}"
location=$(echo "${new_filename}" | cut -d. -f4)

# Define new directory and filename for plex
plex_dir="${dest_dir}/F1 ${year}/Season ${season}"
plex_name="S${season}E${episode} - ${location} Grand Prix - ${key}"
plex_filename="${plex_name}.${extension}"
plex_poster="${plex_name}.png"

mkdir -p "${plex_dir}"

# check to see what network feed the file is. 
# if feed is SKY and we haven't downloaded F1TV feed yet, then let's keep it.
# if feed is SKY and we already downloaded something, abort and delete it 
network=$(echo "${new_filename}" | sed -n "s/.*${key}.//Ip" | sed 's/.WEB.*//')

if [[ -n "$(echo "${network}" | grep -Eio "${preferred_feed}")" ]]; then
  echo "File is Preferred Network (${preferred_feed})."
  echo "Copied"  
  mv "${sab_file}" "${plex_dir}/${plex_filename}"
  echo "Copying poster to ${plex_dir}/${plex_poster}"
  cp "${poster_dir}/${episode}.png" "${plex_dir}/${plex_poster}"
fi

if [[ -z "$(echo "${network}" | grep -Eio "${preferred_feed}")" ]]; then
  if [ ! -f "${plex_dir}/${plex_filename}" ]; then
    echo "File is not Preferred Feed (${preferred_feed}) and file does not exist."
    echo "Copied"
    mv "${sab_file}" "${plex_dir}/${plex_filename}"
    echo "Copying poster to ${plex_dir}/${plex_poster}"
    cp "${poster_dir}/${episode}.png" "${plex_dir}/${plex_poster}"
  fi
  if [ -f "${plex_dir}/${plex_filename}" ]; then
    echo "File is not Preferred Feed (${preferred_feed}) and file already exists."
    echo "Skipped"
    rm -rf "${src_dir}"
    exit 0    
  fi 
fi

echo "Cleaning up sabnzbd files"
rm -rf "${src_dir}"

echo "Setting permissions for ${plex_dir}/${plex_filename}"
chmod 774 "${plex_dir}/${plex_filename}"

echo "Done"
exit 0

