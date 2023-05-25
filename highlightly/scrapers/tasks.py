import logging

import requests
from bs4 import BeautifulSoup

from highlightly.celery import app
from scrapers.models import Match
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

    if not match.finished:
        html = requests.get(url=match.url).text
        soup = BeautifulSoup(html, "html.parser")

        is_live = soup.find("span", class_="match-header-vs-note mod-live")
        if is_live is not None:
            score_spans = soup.find("div", class_="match-header-vs-score").findAll("span")
            game_counts = [int(span.text.strip()) for span in score_spans if span.text.strip().isdigit()]
            game_count = sum(game_counts)

            logging.info(f"Checking if game {match.gamevod_set.count() + 1} of {match} is finished.")
            # TODO: If a new game has started, create an object for the game.
            # TODO: If the current game is finished, start the highlighting process.
            # TODO: If it is the last game of the match, mark the match as finished.
