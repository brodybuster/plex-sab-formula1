#!/bin/bash
# Thanks to https://gist.github.com/scottrobertson for some debugging help

# NZB RSS Feed Keywords: formula1 2025

# sabnzbd RSS Filters:
# 0 : Requires : MWR
# 1 : Reject : re: proper|notebook|multi|round00
# 2 : Requires : re: F1TV|SKY
# 3 : Requires : re: FP1|FP2|FP3|Sprint|Qualifying|Race
# 4 : *

# set to SKY or F1TV
preferred_feed="F1TV"

# set destination dir where to place processed files. 
# should be in your plex media libray path 
# must be accessible from sabnzbd container if you are running sabnzbd in docker
dest_dir="/media/pool.media/formula1"

# poster dir where templates for episode poster reside. 
# must be accessible from sabnzbd container if you are running sabnzbd in docker
poster_dir="/config/scripts/formula_posters"

# set some basic variables we need from sabnzbd
src_dir="$1"
job_name="$3"
sab_file=$(find "$src_dir" -type f | sort -n | tail -1)
extension="${sab_file##*.}"
new_filename="${job_name}.${extension}"

# array of episodes names we are interested in, along with correct eposide number to assign
declare -A episode_array
episode_array["FP1"]="01"
episode_array["Sprint.Qualifying"]="02"
episode_array["Pre-Sprint.Show"]="03"
episode_array["Sprint"]="04"
episode_array["Post-Sprint.Show"]="05"
episode_array["FP2"]="06"
episode_array["FP3"]="07"
episode_array["Pre-Qualifying.Show"]="08"
episode_array["Qualifying"]="09"
episode_array["Post-Qualifying.Show"]="10"
episode_array["Pre-Race.Show"]="11"
episode_array["Race"]="12"
episode_array["Post-Race.Show"]="13"
episode_array["Post-Race.Press.Conference"]="14"

# check to see if filename contains any of the episodes we are interested in
found=0
for key in "${!episode_array[@]}"; do
  if [ -n "$(echo "${new_filename}" | grep -Eio "\.${key}")" ]; then
    found=1
    break
 fi
done

# if filename does not contain wanted episode name, then stop and delete files
if [[ $found -eq 0 ]]; then
  echo "Filename does not contain wanted episode criteria ... aborting"
  rm -rf "${src_dir}"
  exit 1
fi

# extract info we need to rename for plex
year=$(echo "${new_filename}" | cut -d. -f2)
season=$(echo "${new_filename}" | cut -d. -f3 | sed 's/Round//')
episode="${episode_array["${key}"]}"
location=$(echo "${new_filename}" | cut -d. -f4)

# define new directory and filename for plex
plex_dir="${dest_dir}/F1 ${year}/Season ${season}"
plex_name="S${season}E${episode} - ${location} Grand Prix - ${key}"
plex_filename="${plex_name}.${extension}"
plex_poster="${plex_name}.png"

# create needed directories
mkdir -p "${plex_dir}"

# check to see what network feed the file is. 
# if feed is preferred feed we keep it, even if it's been downloaded before.
# if feed is NOT preferred feed, then we only keep it if we don't already have a downloaded file
# the non preferred file will get overwritten if a preferred feed one becomes available
network=$(echo "${new_filename}" | sed -n "s/.*${key}.//Ip" | sed 's/.WEB.*//')

if [[ -n "$(echo "${network}" | grep -Eio "${preferred_feed}")" ]]; then
  echo "File is Preferred Network (${preferred_feed})."
  mv "${sab_file}" "${plex_dir}/${plex_filename}"
  echo "Copied"  
  echo "Copying poster to ${plex_dir}/${plex_poster}"
  cp "${poster_dir}/${episode}.png" "${plex_dir}/${plex_poster}"
else
  if [ ! -f "${plex_dir}/${plex_filename}" ]; then
    echo "File is not Preferred Feed (${preferred_feed}) and file does not exist."
    mv "${sab_file}" "${plex_dir}/${plex_filename}"
    echo "Copied"
    echo "Copying poster to ${plex_dir}/${plex_poster}"
    cp "${poster_dir}/${episode}.png" "${plex_dir}/${plex_poster}"
  else
    echo "File is not Preferred Feed (${preferred_feed}) and file already exists."
    echo "Skipped"
    rm -rf "${src_dir}"
    exit 0    
  fi 
fi

# remove sabnzbd files that are left over
echo "Cleaning up sabnzbd files"
rm -rf "${src_dir}"

# set user friendly permissions 
echo "Setting permissions for ${plex_dir}/${plex_filename}"
chmod 774 "${plex_dir}/${plex_filename}"

echo "Done"
exit 0
