from highlightly.celery import app


@app.task(bind=True)
def scrape_counter_strike_matches(self):
    print(f"Request: {self.request!r}")


@app.task(bind=True)
def scrape_valorant_matches(self):
    print(f"Request: {self.request!r}")


@app.task(bind=True)
def scrape_league_of_legends_matches(self):
    print(f"Request: {self.request!r}")
