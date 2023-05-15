from datetime import datetime

import requests
from bs4 import BeautifulSoup, Tag

from scrapers.models import Match, Game
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
    def extract_team_data(match_team_data: dict) -> TeamData:
        """Parse through the match team data to extract the team data that can be used to create a team object."""
        pass

    @staticmethod
    def is_match_finished(scheduled_match: Match) -> BeautifulSoup | None:
        pass

    @staticmethod
    def download_match_files(match:Match, html: BeautifulSoup) -> None:
        pass

    @staticmethod
    def extract_match_statistics(match: Match, html: BeautifulSoup) -> None:
        pass


def extract_match_data(team_names: list[str], time: str, match_row: Tag) -> dict:
    """Extract the match data from the tag."""
    team_1 = {"name": team_names[0]}
    team_2 = {"name": team_names[1]}

    match_url = f"https://www.vlr.gg{match_row['href']}"

    date = match_row.parent.find_previous_sibling().text.strip()
    date = date.replace("\n", "").replace("\t", "").replace("Today", "").strip()
    start_datetime = datetime.strptime(f"{date} {time}", "%a, %b %d, %Y %I:%M %p")

    return {"game": Game.VALORANT, "team_1": team_1, "team_2": team_2, "start_datetime": start_datetime,
            "format": Match.Format.BEST_OF_3, "tier": 1, "url": match_url}
