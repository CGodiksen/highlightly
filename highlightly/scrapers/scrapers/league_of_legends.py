from scrapers.scrapers.scraper import Scraper


class LeagueOfLegendsScraper(Scraper):
    """Webscraper that scrapes op.gg for upcoming League of Legends matches."""

    @staticmethod
    def list_upcoming_matches() -> list:
        return []

    @staticmethod
    def create_scheduled_match(match) -> None:
        pass
