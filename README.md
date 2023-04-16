# Highlightly Backend
Backend for the Highlightly website for generating highlight videos for esport matches. Currently no games are supported, support is planned for Valorant, Counter-Strike, and League of Legends.

## Scraping for matches
The first step is to scrape for matches that should be made highlight videos for. The scrapers are designed to scrape for as many matches as possible to make it easier to select and deselect matches that should be made videos for. Based on the tier of the game, some matches are pre-selected.

### Counter-Strike
For Counter-Strike, matches are scraped from the HLTV.org website. The teams playing, start time, estimated end time, tier out of 5, tournament, match type (bo3, bo5), hltv match page URL, and tournament context (semi-final, final) is extracted. The logos of the teams playing and the logo of the tournament are also extracted if they do not already exist in the cache. This cache is cleared regularly to avoid issues with teams and tournaments changing logos.

The above is for pre-game scraping, when getting close to the estimated end time, the match page URL should be repeatedly checked for if the match is done. Based on the current result the estimated end time can be changed. When finished the GOTV demo should be downloaded and the VOD for each game should be downloaded based on the length of the GOTV demo. Furthermore, to make it possible to show statistics at the end of the game the per-player statistics is extracted. The MVP of the game is also extracted. 

### Valorant

### League of Legends

## Creating video metadata

## Extracting highlights

## Creating videos
