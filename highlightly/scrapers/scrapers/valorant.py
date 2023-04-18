from scrapers.scrapers.scraper import Scraper


class ValorantScraper(Scraper):
    """Webscraper that scrapes vlr.gg for upcoming Valorant matches."""

    @staticmethod
    def list_upcoming_matches() -> list:
        return []

    @staticmethod
    def create_scheduled_match(match) -> None:
        pass
