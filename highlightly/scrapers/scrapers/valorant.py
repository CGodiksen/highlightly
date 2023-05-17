import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag

from scrapers.models import Match, Game, Organization
from scrapers.scrapers.scraper import Scraper
from scrapers.types import TeamData


class ValorantScraper(Scraper):
    """Webscraper that scrapes vlr.gg for upcoming Valorant matches."""

    included_tournaments = ["Champions Tour 2023: Americas League", "Champions Tour 2023: EMEA League",
                            "Champions Tour 2023: Pacific League", "Champions Tour 2023: Masters Tokyo",
                            "Challengers League: North America"]

    def list_upcoming_matches(self) -> list[dict]:
        """Scrape vlr.gg for upcoming Valorant matches."""
        upcoming_matches = []
        html = requests.get(url="https://www.vlr.gg/matches").text
        soup = BeautifulSoup(html, "html.parser")

        # Find all match rows.
        match_rows = soup.findAll("a", class_="match-item")

        # For each match, extract the data necessary to create a tournament, teams, and match objects.
        for match_row in match_rows:
            tournament_name = match_row.find("div", class_="match-item-event").text.split("\n")[-1].strip()
            team_names = [team.text.strip() for team in match_row.findAll("div", class_="match-item-vs-team-name")]
            time = match_row.find("div", class_="match-item-time").text.strip()

            # Only add the match if is from an included tournament, both teams are determined, and the time is determined.
            if tournament_name in self.included_tournaments and "TBD" not in team_names and time != "TBD":
                match_data = extract_match_data(team_names, time, match_row)
                match_data["tournament_name"] = tournament_name

                upcoming_matches.append(match_data)

        return upcoming_matches

    @staticmethod
    def extract_team_data(match_team_data: dict, organization: Organization) -> TeamData:
        """Parse through the match team data to extract the team data that can be used to create a team object."""
        team_name = match_team_data["name"]

        # Find the URL of the team page.
        html = requests.get(url=match_team_data["match_url"]).text
        match_soup = BeautifulSoup(html, "html.parser")
        team_anchor = next(tag for tag in match_soup.findAll("a", class_="match-header-link") if team_name in tag.text)
        team_url = f"https://www.vlr.gg{team_anchor['href']}"

        # Find the nationality and ranking of the team from the team page.
        html = requests.get(url=team_url).text
        team_soup = BeautifulSoup(html, "html.parser")

        nationality = team_soup.find("div", class_="team-header-country").text.strip()
        ranking = int(team_soup.find("div", class_="rank-num mod-").text.strip())

        # Download the team logo and get the filename.
        team_logo_img = team_soup.find("div", class_="team-header-logo").find("img")
        team_logo_url = f"https:{team_logo_img['src']}"

        if organization.logo_filename is None:
            logo_filename = f"{team_name.replace(' ', '_')}.png"
            Path("media/teams").mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(team_logo_url, f"media/teams/{logo_filename}")

            organization.logo_filename = logo_filename
            organization.save()

        return {"url": team_url, "nationality": nationality, "ranking": ranking}

    @staticmethod
    def is_match_finished(scheduled_match: Match) -> BeautifulSoup | None:
        """Return the page HTML if the match is finished and ready for further processing. Otherwise, return None."""
        html = requests.get(url=scheduled_match.url).text
        soup = BeautifulSoup(html, "html.parser")

        status = soup.find("div", class_="match-header-vs-note").text

        return html if status == "final" else None

    @staticmethod
    def download_match_files(match: Match, html: BeautifulSoup) -> None:
        """Download a VOD for each game in the match."""
        # Find the best stream url for the match.
        stream_divs = html.findAll("div", class_="match-streams-btn")
        stream_url = stream_divs[0].find("a")["href"]

        valid_stream_languages = ["mod-un", "mod-eu", "mod-us", "mod-au"]
        banned_streams = ["https://www.twitch.tv/valorant"]

        for stream_div in stream_divs:
            stream_flag = stream_div.find("i", class_="flag")
            stream_div_url = stream_div.find("a")["href"]

            # Only allow stream urls from english speaking streams and non-banned streams.
            if stream_flag["class"][1] in valid_stream_languages and stream_div_url not in banned_streams:
                stream_url = stream_div_url
                break

        # Find the latest video from the stream which should be the video with the VOD for each game.
        list_videos_cmd = f"twitch-dl videos {stream_url.split('/')[-1]}"
        result = subprocess.run(list_videos_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

        print(result.stdout)

        # TODO: For each game, download the VOD for the game from the Twitch video.

    @staticmethod
    def extract_match_statistics(match: Match, html: BeautifulSoup) -> None:
        pass


def extract_match_data(team_names: list[str], time: str, match_row: Tag) -> dict:
    """Extract the match data from the tag."""
    match_url = f"https://www.vlr.gg{match_row['href']}"

    team_1 = {"name": team_names[0], "match_url": match_url}
    team_2 = {"name": team_names[1], "match_url": match_url}

    date = match_row.parent.find_previous_sibling().text.strip()
    date = date.replace("\n", "").replace("\t", "").replace("Today", "").strip()
    start_datetime = datetime.strptime(f"{date} {time}", "%a, %b %d, %Y %I:%M %p")

    # TODO: Find the actual format and tier.
    return {"game": Game.VALORANT, "team_1": team_1, "team_2": team_2, "start_datetime": start_datetime,
            "format": Match.Format.BEST_OF_3, "tier": 1, "url": match_url}
