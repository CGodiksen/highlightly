from datetime import datetime
from typing import TypedDict

from scrapers.models import ScheduledMatch


class Match(TypedDict):
    url: str
    team_1: str
    team_2: str
    start_datetime: datetime
    tier: int
    format: ScheduledMatch.Format
    tournament_name: str
