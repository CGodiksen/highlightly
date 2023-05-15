import requests
from bs4 import BeautifulSoup

from scrapers.models import Match
from scrapers.scrapers.scraper import Scraper
from scrapers.types import TeamData


class ValorantScraper(Scraper):
    """Webscraper that scrapes vlr.gg for upcoming Valorant matches."""

    included_tournaments = ["Champions Tour 2023: Americas League", "Champions Tour 2023: EMEA League",
                            "Champions Tour 2023: Pacific League", "Champions Tour 2023: Masters Tokyo",
                            "Challengers League: North America"]

    def list_upcoming_matches(self) -> list[dict]:
        html = requests.get(url="https://www.vlr.gg/matches").text
        soup = BeautifulSoup(html, "html.parser")

        # Find all match rows.
        match_rows = soup.findAll("a", class_="match-item")

        # For each match, extract the data necessary to create a tournament, teams, and match objects.
        for match_row in match_rows:
            tournament_name = match_row.find("div", class_="match-item-event").text.split("\n")[-1].strip()
            team_names = [team.text.strip() for team in match_row.findAll("div", class_="match-item-vs-team-name")]

            # Only add the match if is from an included tournament and both teams are determined.
            if tournament_name in self.included_tournaments and "TBD" not in team_names:
                print(team_names)

        return []

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
