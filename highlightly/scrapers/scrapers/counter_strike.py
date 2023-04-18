import requests
from bs4 import BeautifulSoup

from scrapers.scrapers.scraper import Scraper


class CounterStrikeScraper(Scraper):
    """Webscraper that scrapes hltv.org for upcoming Counter-Strike matches."""

    @staticmethod
    def list_upcoming_matches() -> list:
        matches_url = "https://www.hltv.org/matches"
        html = requests.get(url=matches_url).text

        soup = BeautifulSoup(html, "html.parser")
        print(soup.prettify())

        return []

    @staticmethod
    def filter_already_scheduled_matches(matches: list) -> list:
        return matches

    @staticmethod
    def create_scheduled_match(match) -> None:
        pass
