from datetime import datetime
from typing import TypedDict

from scrapers.models import ScheduledMatch


class Match(TypedDict):
    match_url: str
    start_datetime: datetime
    tier: int
    format: ScheduledMatch.Format
    tournament_name: str
    tournament_url: str
