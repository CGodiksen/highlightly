from bs4 import BeautifulSoup

from scrapers.models import Tournament, Team, Match
from scrapers.scrapers.scraper import Scraper
from scrapers.types import MatchData


class ValorantScraper(Scraper):
    """Webscraper that scrapes vlr.gg for upcoming Valorant matches."""

    @staticmethod
    def list_upcoming_matches() -> list[MatchData]:
        pass

    @staticmethod
    def create_tournament(match: MatchData) -> Tournament:
        pass

    @staticmethod
    def create_team(team_name, team_id) -> Team:
        pass

    @staticmethod
    def create_scheduled_match(match: MatchData, tournament: Tournament, team_1: Team, team_2: Team) -> None:
        pass

    @staticmethod
    def is_match_finished(scheduled_match: Match) -> BeautifulSoup | None:
        pass

    @staticmethod
    def download_match_files(match:Match, html: BeautifulSoup) -> None:
        pass

    @staticmethod
    def extract_match_statistics(html: BeautifulSoup) -> None:
        pass
