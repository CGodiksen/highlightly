from highlightly.celery import app
from scrapers.scrapers.counter_strike import CounterStrikeScraper
from scrapers.scrapers.league_of_legends import LeagueOfLegendsScraper
from scrapers.scrapers.valorant import ValorantScraper


@app.task
def scrape_counter_strike_matches() -> None:
    scraper = CounterStrikeScraper()
    scraper.scrape()


@app.task
def scrape_valorant_matches() -> None:
    scraper = ValorantScraper()
    scraper.scrape()


@app.task
def scrape_league_of_legends_matches() -> None:
    scraper = LeagueOfLegendsScraper()
    scraper.scrape()
