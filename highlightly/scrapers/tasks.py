from django_celery_beat.models import PeriodicTask

from highlightly.celery import app
from scrapers.models import ScheduledMatch
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
def check_if_counter_strike_match_finished(scheduled_match_id: int) -> None:
    scheduled_match = ScheduledMatch.objects.get(id=scheduled_match_id)
    scraper = CounterStrikeScraper()

    if scraper.is_match_finished(scheduled_match):
        periodic_task = PeriodicTask.objects.get(name=f"Check if {scheduled_match} is finished")
        periodic_task.delete()

        scheduled_match.finished = True
        scheduled_match.save()
