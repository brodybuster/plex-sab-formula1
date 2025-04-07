Instructions on how to use a SABnzbd Post Processing Script to help organize your Formula 1 Collection

Prerequistes:
Plex (should work with other media servers)
Sabnzbd
NZB indexer with custom RSS Feeds 

I will assume that you have your media server and sabnzbd running correctly. This will work on baremetal or docker installations. 

1. Prepare your NZB RSS Feed.
  a. I use the following key words: "Forumula1 2025"
  b. Grab the RSS feed link

2. Prepare sabnzbd 
a. Create a new RSS feed
b. use the following filters. This will filter all releases from MWR (which I prefer)
0 : Requires : MWR
1 : Reject : re: proper|notebook|multi|round00
2 : Requires : re: F1TV|SKY
3 : Requires : re: FP1|FP2|FP3|Sprint|Qualifying|Race
4 : *

   

