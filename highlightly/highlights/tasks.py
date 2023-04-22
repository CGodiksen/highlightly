import requests
from bs4 import BeautifulSoup
from django_celery_beat.models import PeriodicTask

from highlightly.celery import app
from highlights.highlighters.counter_strike import CounterStrikeHighlighter
from highlights.highlighters.league_of_legends import LeagueOfLegendsHighlighter
from highlights.highlighters.valorant import ValorantHighlighter
from scrapers.models import ScheduledMatch, Game
from videos.metadata.post_match import add_post_match_video_metadata


@app.task
def check_if_match_finished(scheduled_match_id: int) -> None:
    """
    Check if the scheduled match is finished. If finished, mark the scheduled match as finished, create highlights
    for the match, and extract post-match metadata for the match.
    """
    scheduled_match = ScheduledMatch.objects.get(id=scheduled_match_id)

    if is_match_finished(scheduled_match):
        periodic_task = PeriodicTask.objects.get(name=f"Check if {scheduled_match} is finished")
        periodic_task.delete()

        scheduled_match.finished = True
        scheduled_match.save()

        if scheduled_match.team_1.game == Game.COUNTER_STRIKE:
            highlighter = CounterStrikeHighlighter()
        elif scheduled_match.team_1.game == Game.VALORANT:
            highlighter = ValorantHighlighter()
        else:
            highlighter = LeagueOfLegendsHighlighter()

        highlighter.highlight(scheduled_match)
        add_post_match_video_metadata(scheduled_match)


def is_match_finished(scheduled_match: ScheduledMatch) -> bool:
    """Return True if the match is finished and ready for further processing."""
    html = requests.get(url="https://www.hltv.org/results").text
    soup = BeautifulSoup(html, "html.parser")

    # Check if the scheduled match url can be found on the results page.
    match_url_postfix = scheduled_match.url.removeprefix("https://www.hltv.org")
    return soup.find("a", class_="a-reset", href=match_url_postfix) is not None
