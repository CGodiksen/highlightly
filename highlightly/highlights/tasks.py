from highlightly.celery import app
from scrapers.models import ScheduledMatch


@app.task
def check_if_match_is_finished(scheduled_match: ScheduledMatch) -> None:
    """
    Check if the scheduled match is finished. If finished, mark the scheduled match as finished, create highlights
    for the match, and create post-game metadata for the match.
    """
    scheduled_match.finished = True
    scheduled_match.save()

    
