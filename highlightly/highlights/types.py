from typing import TypedDict


class Event(TypedDict):
    name: str
    time_since_start: int

class PlayerEvent(Event):
    player_1: str | None
    player_2: str | None
