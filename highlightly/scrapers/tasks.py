from highlightly.celery import app
from scrapers.scrapers import counter_strike


@app.task(bind=True)
def scrape_counter_strike_matches(self) -> None:
    """
    Scrape hltv.org for upcoming Counter-Strike matches. For each new match that is found, a ScheduledMatch object is
    created. If the match already exists, the match is ignored.
    """
    # List the current upcoming matches in HLTV.
    matches = counter_strike.list_upcoming_matches()
    new_matches = counter_strike.filter_already_scheduled_matches(matches)

    # For each remaining match in the list, create a ScheduledMatch object.
    for match in new_matches:
        # TODO: When a scheduled match is created a websocket message should be sent.
        counter_strike.create_scheduled_match(match)

    print(f"Request: {self.request!r}")


@app.task(bind=True)
def scrape_valorant_matches(self) -> None:
    """
    Scrape vlg.gg for upcoming Valorant matches. For each new match that is found, a ScheduledMatch object is created.
    If the match already exists, the match is ignored.
    """
    print(f"Request: {self.request!r}")


@app.task(bind=True)
def scrape_league_of_legends_matches(self) -> None:
    """
    Scrape op.gg for upcoming League of legends matches. For each new match that is found, a ScheduledMatch object is
    created. If the match already exists, the match is ignored.
    """
    print(f"Request: {self.request!r}")
