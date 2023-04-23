from datetime import datetime, date
from typing import TypedDict

from scrapers.models import Match, Tournament


class MatchData(TypedDict):
    url: str
    team_1_id: int
    team_1_name: str
    team_2_id: int
    team_2_name: str
    start_datetime: datetime
    tier: int
    format: Match.Format
    tournament_name: str


class TournamentData(TypedDict):
    start_date: date
    end_date: date
    prize_pool: str
    first_place_prize: str
    location: str
    tier: int
    type: Tournament.Type
