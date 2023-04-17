from scrapers.scrapers.scraper import Scraper


class CounterStrikeScraper(Scraper):
    """Webscraper that scrapes hltv.org for upcoming Counter-Strike matches."""

    @staticmethod
    def list_upcoming_matches() -> list:
        return []

    @staticmethod
    def filter_already_scheduled_matches(matches: list) -> list:
        return matches

    @staticmethod
    def create_scheduled_match(match) -> None:
        pass
