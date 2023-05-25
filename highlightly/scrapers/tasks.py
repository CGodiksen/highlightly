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
    logging.info(f"Checking the match status of {match}.")

    if not match.finished:
        html = requests.get(url=match.url).text
        soup = BeautifulSoup(html, "html.parser")

        # If it is the last game of the match, mark the match as finished.
        if "final" in soup.find("div", class_="match-header-vs-note").text:
            logging.info(f"{match} is finished.")

        # Find the current number of finished games.
        score_spans = soup.find("div", class_="match-header-vs-score").findAll("span")
        game_counts = [int(span.text.strip()) for span in score_spans if span.text.strip().isdigit()]
        finished_game_count = sum(game_counts)

        # If a new game has started, create an object for the game.
        is_live = soup.find("span", class_="match-header-vs-note mod-live")
        if is_live is not None and not match.gamevod_set.filter(game_count=finished_game_count + 1).exists():
            logging.info(f"Game {finished_game_count + 1} for {match} has started. Creating object for game.")

        # Check if the most recently finished game has been marked as finished.
        if match.gamevod_set.filter(game_count=finished_game_count).exists():
            finished_game = match.gamevod_set.get(game_count=finished_game_count)
            if not finished_game.finished:
                logging.info(f"Game {finished_game_count} for {match} is finished. Starting highlighting process.")
