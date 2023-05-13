from datetime import datetime, date
from typing import TypedDict

from scrapers.models import Match, Tournament


class CounterStrikeTeamData(TypedDict):
    id: int
    name: str


class CounterStrikeMatchData(TypedDict):
    url: str
    team_1: CounterStrikeTeamData
    team_2: CounterStrikeTeamData
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
