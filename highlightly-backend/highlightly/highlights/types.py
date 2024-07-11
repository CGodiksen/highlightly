from typing import TypedDict


class Event(TypedDict):
    name: str
    time: int
    info: int | str | None


class RoundData(TypedDict):
    number: int
    events: list[Event]
    end_time: int
    teams: list[int]
    winner: int
    team_1_alive: int
    team_2_alive: int
    team_1_equipment_value: int
    team_2_equipment_value: int


class SecondData(TypedDict):
    round_time_left: int
    round_number: int
    events: list[Event]
