import logging

import requests
from bs4 import BeautifulSoup

from highlightly.celery import app
from scrapers.models import Match, Game
from scrapers.scrapers.counter_strike import CounterStrikeScraper
from scrapers.scrapers.league_of_legends import LeagueOfLegendsScraper
from scrapers.scrapers.valorant import ValorantScraper


@app.task
def scrape_counter_strike_matches() -> None:
    scraper = CounterStrikeScraper()
    scraper.scrape_upcoming_matches()


@app.task
def scrape_valorant_matches() -> None:
    scraper = ValorantScraper()
    scraper.scrape_upcoming_matches()


@app.task
def scrape_league_of_legends_matches() -> None:
    scraper = LeagueOfLegendsScraper()
    scraper.scrape_upcoming_matches()


@app.task
def scrape_finished_counter_strike_match(scheduled_match_id: int) -> None:
    scheduled_match = Match.objects.get(id=scheduled_match_id)

    scraper = CounterStrikeScraper()
    scraper.scrape_finished_match(scheduled_match)


@app.task
def scrape_finished_valorant_match(scheduled_match_id: int) -> None:
    scheduled_match = Match.objects.get(id=scheduled_match_id)

    scraper = ValorantScraper()
    scraper.scrape_finished_match(scheduled_match)


@app.task
def scrape_finished_league_of_legends_match(scheduled_match_id: int) -> None:
    scheduled_match = Match.objects.get(id=scheduled_match_id)

    scraper = LeagueOfLegendsScraper()
    scraper.scrape_finished_match(scheduled_match)


@app.task
def check_match_status(match_id: int) -> None:
    """Check the current match status."""
    match = Match.objects.get(id=match_id)
    logging.info(f"Checking the status of {match}.")

    if not match.finished:
        if match.team_1.game == Game.VALORANT:
            scraper = ValorantScraper()
            scraper.check_match_status(match)
