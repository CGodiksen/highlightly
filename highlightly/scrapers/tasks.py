from highlightly.celery import app
from scrapers.scrapers.counter_strike import CounterStrikeScraper
from scrapers.scrapers.league_of_legends import LeagueOfLegendsScraper
from scrapers.scrapers.valorant import ValorantScraper


@app.task(bind=True)
def scrape_counter_strike_matches(self) -> None:
    scraper = CounterStrikeScraper()
    scraper.scrape()

    print(f"Request: {self.request!r}")


@app.task(bind=True)
def scrape_valorant_matches(self) -> None:
    scraper = ValorantScraper()
    scraper.scrape()

    print(f"Request: {self.request!r}")


@app.task(bind=True)
def scrape_league_of_legends_matches(self) -> None:
    scraper = LeagueOfLegendsScraper()
    scraper.scrape()

    print(f"Request: {self.request!r}")
