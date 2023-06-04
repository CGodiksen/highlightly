from datetime import datetime, date
from typing import TypedDict

from scrapers.models import Match, Tournament, Game


class CounterStrikeMatchData(TypedDict):
    url: str
    team_1: dict
    team_2: dict
    start_datetime: datetime
    tier: int
    format: Match.Format
    tournament_name: str
    game: Game


class TournamentData(TypedDict):
    start_date: date
    end_date: date
    prize_pool: str
    first_place_prize: str
    location: str
    tier: int
    type: Tournament.Type


class TeamData(TypedDict):
    url: str
    nationality: str
    ranking: int | None
