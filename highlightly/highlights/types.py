from typing import TypedDict


class Event(TypedDict):
    name: str
    time: int


class Round(TypedDict):
    round_number: int
    events: list[Event]
