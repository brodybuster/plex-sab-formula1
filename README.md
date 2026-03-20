## Note: This script is meant to work with MWR or BILLIE for the 2026 Season

## 1. Create a Custom RSS feed in your NZB Indexer Provider
* I use the following key words: formula1 2026

## 2. SABnzbd

- Place the `formula1_sabnzbd.sh` script into the script directory defined in your SABnzbd configuration. Make sure it is executable.
- Download the `formula_posters` directory and place it somewhere SABnzbd can access it. To keep things simple, place it in the same directory as `formula1_sabnzbd.sh`.
- If you are using Docker, make sure both the script path and the poster path are accessible from inside the SABnzbd container.
- Edit the paths in the script to match your environment. Both `DEST_DIR` and the poster directories must be writable and accessible by SABnzbd.
- The script is designed to prefer `F1LIVE` coverage over `SKY`, while still allowing `SKY` releases to be downloaded until a preferred release becomes available.
- Copy and paste the custom RSS feed URL from your indexer into a new RSS feed in SABnzbd.

Add the following filters and choose the `formula1_sabnzbd.sh` script for post-processing for your new RSS Feed:

Recommended SABnzbd RSS Filters:

```text
0 : Requires : re: MWR|BILLIE
1 : Reject : re: proper|notebook|multi|round00|academy|warmup|race\.one|race\.two|sprint\.race\.one|sprint\.race\.two
2 : Requires : re: 1080p
3 : Requires : re: FP1|FP2|FP3|Sprint|Qualifying|Race|Practice\.One|Practice\.Two|Practice\.Three|Grand\.Prix
4 : *
```

* Press **Read Feed**, then **Apply Filters**
* Note: On the first loading of the feed you will need to Force Download any files that qualify. Subsequent RSS Feeds will be automatically refreshed every hour. 

## 3. Set your agent for Plex Media Shows to use local assets
<img width="500" alt="Screenshot 2025-04-07 at 1 51 02 PM" src="https://github.com/user-attachments/assets/07fc730e-6d56-4e23-9a98-4df9623a2019" />

## 4. Folder Structure

The script expects a base Formula 1 library folder to already exist. From there, it will automatically create the year and season folders it needs as new content is processed.

### Required Base Folder

You must create the main Formula 1 library folder manually.

Example:
`/media/pool.media/formula1`

This should match the `DEST_DIR` value defined in the script.

### Automatically Created by the Script

Once the base folder exists, the script will automatically create:

- year folders such as `F1 2026`
- season folders such as `Season 01`
- renamed media files such as `S01E01 - Australia Grand Prix - FP1.mkv`
- episode poster files such as `S01E01 - Australia Grand Prix - FP1.png`
- season poster files such as `season01.png`

### Example Structure

```text
formula1                         (must be created manually)
└── F1 2026                      (created automatically by the script)
    ├── Season 01                (created automatically by the script)
    │   ├── season01.png         (copied by the script if a matching season poster exists)
    │   ├── S01E01 - Australia Grand Prix - FP1.mkv
    │   ├── S01E01 - Australia Grand Prix - FP1.png
    │   ├── S01E02 - Australia Grand Prix - FP2.mkv
    │   └── S01E02 - Australia Grand Prix - FP2.png
    └── Season 02                (created automatically by the script)
```

### What Must Be Created Manually

You must create:

- the base Formula 1 library folder defined by `DEST_DIR`
- the source poster folders if you want automatic poster support:
  - `formula_posters/episode/`
  - `formula_posters/season/`
- the source poster image files stored inside those folders

### What the Script Handles Automatically

The script will:

- create year folders such as `F1 2026`
- create season folders such as `Season 01`
- move and rename the processed video file into the correct Plex folder
- copy a matching episode poster into the season folder if one exists
- copy a matching season poster into the season folder if one exists

### Important Note

The script does not generate poster artwork.

It only copies poster files that already exist in the configured poster directories. If no matching poster file is found, the media file will still be imported normally.


## 5. Create a new library for your Formula 1 Show
<img width="500" alt="Screenshot 2025-04-07 at 1 48 43 PM" src="https://github.com/user-attachments/assets/42296cae-ee32-4077-8497-572fca15b7db" />
<img width="500" alt="Screenshot 2025-04-07 at 1 48 54 PM" src="https://github.com/user-attachments/assets/71a7e9d6-8346-47dd-b2e0-e2a9f4721dca" />
<img width="500" alt="Screenshot 2025-04-07 at 1 49 02 PM" src="https://github.com/user-attachments/assets/75f00ee0-7ec5-4ea4-b3a2-05ac38916c21" />
<img width="500" alt="Screenshot 2025-04-07 at 1 49 15 PM" src="https://github.com/user-attachments/assets/34530ed6-aee1-4531-ae61-cd3e8c4df2a6" />
<img width="500" alt="Screenshot 2025-04-07 at 1 49 23 PM" src="https://github.com/user-attachments/assets/8b0873b7-a099-4a03-a0be-9cab98ebffab" />

## 6. Season and Episode Posters

There are two ways to manage posters: `Automatic` and `Manual`.

### Automatic

The script can automatically copy both episode and season poster artwork into the correct Plex folder during processing.

**Episode posters**

Place episode poster source images in `formula_posters/episode/`.

These files must be named using the episode number expected by the script.

Examples:

- `formula_posters/episode/01.png`
- `formula_posters/episode/02.png`
- `formula_posters/episode/12.png`

**Season posters**

Place season poster source images in `formula_posters/season/`.

These files must be named using the season number parsed by the script. In this setup, the season number corresponds to the Formula 1 round number.

Examples:

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

**Important**

- Filenames must match exactly.
- Use `.png` files only.
- Episode posters must use the script’s mapped episode number, not the event name.
- Season posters must use the parsed season number from the release filename.

### Manual

If you prefer not to use local poster files, you can manage artwork directly in Plex instead.

Plex documentation for local media assets:  
[https://support.plex.tv/articles/200220717-local-media-assets-tv-shows/](https://support.plex.tv/articles/200220717-local-media-assets-tv-shows/)

## 7. Examples
   
**Non-Sprint Weekend**

<img width="500" alt="Screenshot 2025-04-07 at 2 43 59 PM" src="https://github.com/user-attachments/assets/2f1a32b2-6dbb-48ef-beb7-7fa9e91b11e2" />



**Sprint Weekend**

<img width="500" alt="Screenshot 2025-04-07 at 2 51 05 PM" src="https://github.com/user-attachments/assets/815a8ae6-eef7-4764-9130-822522c84a16" />


**Seasons**

<img width="500" alt="Screenshot 2025-04-07 at 2 55 58 PM" src="https://github.com/user-attachments/assets/7cea3ce8-e41d-4d4c-a5e1-40721a2d8730" />
