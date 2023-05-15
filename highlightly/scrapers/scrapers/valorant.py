from bs4 import BeautifulSoup

from scrapers.models import Tournament, Team, Match
from scrapers.scrapers.scraper import Scraper
from scrapers.types import TeamData


class ValorantScraper(Scraper):
    """Webscraper that scrapes vlr.gg for upcoming Valorant matches."""

    @staticmethod
    def list_upcoming_matches() -> list[dict]:
        pass

    @staticmethod
    def extract_team_data(match_team_data: dict) -> TeamData:
        """Parse through the match team data to extract the team data that can be used to create a team object."""
        pass

    @staticmethod
    def create_scheduled_match(match: dict, tournament: Tournament, team_1: Team, team_2: Team) -> None:
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
