from datetime import datetime, date
from typing import TypedDict

from scrapers.models import ScheduledMatch, Tournament


class MatchData(TypedDict):
    url: str
    team_1: str
    team_2: str
    start_datetime: datetime
    tier: int
    format: ScheduledMatch.Format
    tournament_name: str
    tournament_logo_url: str


class TournamentData(TypedDict):
    start_date: date
    end_date: date
    prize_pool: str
    first_place_prize: str
    location: str
    tier: int
    type: Tournament.Type
