from typing import TypedDict


class Event(TypedDict):
    name: str
    time: int
    info: int | str | None


class Round(TypedDict):
    round_number: int
    events: list[Event]


class RoundData(TypedDict):
    number: int
    events: list[Event]
    end_time: int
    winner: int
    team_1_alive: int
    team_2_alive: int
    team_1_equipment_value: int
    team_2_equipment_value: int
