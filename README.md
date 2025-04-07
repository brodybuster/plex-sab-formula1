# 1. Create a Custom RSS feed in your NZB Indexer Provider
* I use the following key words: formula1 2025

# 2. SABnzbd
* Place the **formula_sabnzbd.sh** script into the script directory defined in your sabnzbd config. Make sure its executable.
* Download the **formula_posters** dir and place it where sabnzbd can access them. To keep it simple, place it in the same directory you placed the **formula_sabnzbd.sh** script. Make sure this path is accessible by your sabnzbd container if you are using docker. 
* Edit the directories in the script to suit your needs, both the **dest_dir** and the **poster_dir** need to be accessible by your docker container if you are using docker. Also ensure that sabnzbd has permission to access/write to these directories.
* The code is pretty well commented, feel free to make any changes to your liking. It's setup to prefer F1LIVE coverage over SKY coverage, but to download SKY coverage until F1LIVE is available. 
* Copy and Paste the link for the Custom RSS Feed from your Indexer into a new Feed in Sabnzbd

<img width="1133" alt="Screenshot 2025-04-07 at 2 19 55 PM" src="https://github.com/user-attachments/assets/04891138-0bb7-435c-bfe4-d90e63e393a9" />

Add the following filters and choose the formula_sabnzbd.sh script for post-processing for your new RSS Feed:
* 0 : Requires : MWR
* 1 : Reject : re: proper|notebook|multi|round00
* 2 : Requires : re: F1TV|SKY
* 3 : Requires : re: FP1|FP2|FP3|Sprint|Qualifying|Race
* 4 : *

<img width="1127" alt="Screenshot 2025-04-07 at 1 47 08 PM" src="https://github.com/user-attachments/assets/2f3e2028-3727-40a1-a7cd-dddeacbd2b9b" />

* Press **Read Feed**, then **Apply Filters**
* Note: On the first loading of the feed you will need to Force Download any files that qualify. Subsequent RSS Feeds will be automatically refreshed every hour. 

<img width="1131" alt="Screenshot 2025-04-07 at 2 37 50 PM" src="https://github.com/user-attachments/assets/2fa57522-f7d2-4eca-a40d-00ea9322242c" />

# 2. Set your agent for Plex Media Shows to use local assets
<img width="1039" alt="Screenshot 2025-04-07 at 1 51 02 PM" src="https://github.com/user-attachments/assets/07fc730e-6d56-4e23-9a98-4df9623a2019" />

# 3. Create a new library for your Formula 1 Show
<img width="731" alt="Screenshot 2025-04-07 at 1 48 43 PM" src="https://github.com/user-attachments/assets/42296cae-ee32-4077-8497-572fca15b7db" />
<img width="729" alt="Screenshot 2025-04-07 at 1 48 54 PM" src="https://github.com/user-attachments/assets/71a7e9d6-8346-47dd-b2e0-e2a9f4721dca" />
<img width="729" alt="Screenshot 2025-04-07 at 1 49 02 PM" src="https://github.com/user-attachments/assets/75f00ee0-7ec5-4ea4-b3a2-05ac38916c21" />
<img width="731" alt="Screenshot 2025-04-07 at 1 49 15 PM" src="https://github.com/user-attachments/assets/34530ed6-aee1-4531-ae61-cd3e8c4df2a6" />
<img width="731" alt="Screenshot 2025-04-07 at 1 49 23 PM" src="https://github.com/user-attachments/assets/8b0873b7-a099-4a03-a0be-9cab98ebffab" />

# 4. You can now manually set posters for fanart, seasons, etc to your liking in plex once the directories start poplulating. Episode posters are loaded as local assets to the Season folder via the script. 
* I personally create season01.png, season02.png, etc image files that corrospond to each Grand Prix. So for Australia, I created a custom season01.png and placed it into the Season 01 Folder (per plex naming conventions)
* Each Formula Season (2024, 2025, etc), will be one Show in Plex, in your Formula Library
* Each Round of a Season (Round 01, Round 02, etc) will be one Season in the Show.
* All folders are created automatically, except to top level libray folder for plex.


 - formula1 **(needs to be created)**
   - F1 2025 (automatically created by script)
     - Season 01 (automatically created by script)
       - season01.png **(manual creation)**
       - S01E01 - Australia Grand Prix - FP1.mkv (automatically created by script)
       - S01E01 - Australia Grand Prix - FP1.png (automatically created by script)
       - S01E02 - Australia Grand Prix - FP2.mkv (automatically created by script)
       - S01E02 - Australia Grand Prix - FP2.png (automatically created by script)
     - Season 02 (automatically created)

   
**None Sprint Weekend**

<img width="1211" alt="Screenshot 2025-04-07 at 2 43 59 PM" src="https://github.com/user-attachments/assets/2f1a32b2-6dbb-48ef-beb7-7fa9e91b11e2" />



**Sprint Weekend**

<img width="1177" alt="Screenshot 2025-04-07 at 2 51 05 PM" src="https://github.com/user-attachments/assets/815a8ae6-eef7-4764-9130-822522c84a16" />


**season01.png season02.png season03.png examples**

<img width="645" alt="Screenshot 2025-04-07 at 2 55 58 PM" src="https://github.com/user-attachments/assets/7cea3ce8-e41d-4d4c-a5e1-40721a2d8730" />
