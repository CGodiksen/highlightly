# Highlightly Backend
Backend for the Highlightly website for generating highlight videos for esport matches. Currently no games are supported, support is planned for Valorant, Counter-Strike, and League of Legends.

## Scraping for matches
The first step is to scrape for matches that should be made highlight videos for. The scrapers are designed to scrape for as many matches as possible to make it easier to select and deselect matches that should be made videos for. Based on the tier of the match, some matches are pre-selected.

### Counter-Strike
For Counter-Strike, matches are scraped from the [cover.gg](cover.gg) website. The teams playing, start time, estimated end time, tier out of 5, tournament, match type (bo3, bo5), hltv match page URL, and tournament context (semi-final, final) is extracted. The logos of the teams playing and the logo of the tournament are also extracted if they do not already exist in the cache. This cache is cleared regularly to avoid issues with teams and tournaments changing logos.

The above is for pre-game scraping, when getting close to the estimated end time, the match page URL should be repeatedly checked for if the match is done. Based on the current result the estimated end time can be changed. When finished, the GOTV demo should be downloaded and the VOD for each map should be downloaded based on the length of the GOTV demo. Furthermore, to make it possible to show statistics at the end of the video and between maps the per-player and per-map statistics are extracted. The MVP of the match is also extracted. 

### Valorant
For Valorant, matches are scraped from the [vlr.gg](vlr.gg) website. The teams playing, start time, estimated end time, estimated tier out of 5 based on team rankings, tournament, match type (bo3, bo5), vlr match page URL, and tournament context (semi-final, final) is extracted. The logos of the teams playing and the logo of the tournament are also extracted if they do not already exist in the cache. This cache is cleared regularly to avoid issues with teams and tournaments changing logos.

The above is for pre-game scraping, when getting close to the estimated end time, the match page URL should be repeatedly checked for if the match is done. Based on the current result the estimated end time can be changed. When finished, the VOD for each map should be downloaded based on the length of the map extracted from the match page. Furthermore, to make it possible to show statistics at the end of the video and between maps the per-player and per-map statistics are extracted. The MVP of the match is estimated based on the average combat score. 

### League of Legends
For League of Legends, matches are scraped from the [op.gg](https://esports.op.gg/schedules) website. The teams playing, start time, estimated end time, estimated tier out of 5 based on team rankings, tournament, and tournament context (semi-final, final) is extracted. The logos of the teams playing and the logo of the tournament are also extracted if they do not already exist in the cache. This cache is cleared regularly to avoid issues with teams and tournaments changing logos. The logo of the tournament can be extracted from the [LoL Esports](https://lolesports.com/schedule) page. 

The above is for pre-game scraping, when getting close to the estimated end time, the match page URL should be repeatedly checked for if the match is done. Based on the current result the estimated end time can be changed. When finished, the corresponding vod page on the LoL Esports website should be found. The VOD for each map should be downloaded from the page for the game. Furthermore, to make it possible to show statistics at the end of the video and between maps the per-player and per-map statistics are extracted. The MVP of the match is estimated based on the the players statistics (inspired by OP score). 

## Creating video metadata
Based on the extracted metadata about the matches, video metadata should be created. The objective is to generate as much as possible before the game is finished to avoid extra processing after the game. The following is a list of what needs to be generated for each video and how it is generated.

### Pre-game
* Title - Generated based on the teams, tournament and tournament context.
* Description - Generated based on the teams, tournament and links used for external services.
* Tags - Generated based on teams, players, tournament, tournament context and countries.
* Thumbnail - Generated based on in-game image, teams, countries, tournament, and tournament context.
* Game - What game the video is created for.
* Category - Always gaming.

### Post-game
* Scoreboard and general statistics for each map.
* Scoreboard and general statistics for the entire match.
* Screen with image of the MVP and the players statistics over the entire match.

## Extracting highlights
When the vods are downloaded and ready, the next step is cutting the full video into a video that only includes the highlights. The method for finding the segments of the video that need to be kept depends on the specific game but the objective is the same. For each vod the exact time of the game starting in the video needs to be found. Ater this, a timeline of all relevant events in the game can be created and overlayed on the vod. Based on certain parameters, created to make the video short while still capturing all the most relevant moments, actual segments can be cut out of the vod. 

### Counter-Strike
For Counter-Strike we want to capture all kills in the timeline and other large damage events such as hits without killing, grenades, and incendiary damage. Furthermore, we want to capture large round events such as the round starting, bomb being planted, bomb exploding, bomb being defused, and round ending. The full list of events can be found [here](https://wiki.alliedmods.net/Counter-Strike:_Global_Offensive_Events). 

### Valorant
For Valorant we want to capture all kills in the timeline and other large damage events such as hits without killing or damage from a character ability. Furthermore, we want to capture large round events such as the round starting, ultimate abilities being used, spike being planted, spike exploding, spike being defused, and round ending. 

### League of Legends
For League of Legends we want to capture all kills in the timeline and other large damage events such as hits without killing. Furthermore, we want to capture large game events such as the game starting, towers being destroyed, inhibitors being destroyed, dragons being killed, rift heralds being killed, barons being killed, and the nexus being destroyed to end the game. 

## Creating and uploading videos
The highlight segments are put together into a single video with minor extra changes such as adding a longer intro, statistics between each map, and statistics at the end of the game.
