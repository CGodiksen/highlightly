import logging

from highlights.highlighters.highlighter import Highlighter
from highlights.types import SecondData
from scrapers.models import GameVod


class ValorantHighlighter(Highlighter):
    """Highlighter that uses PaddleOCR to extract highlights from Valorant matches."""

    def extract_events(self, game: GameVod) -> dict[int, SecondData]:
        """Parse through the match to find all significant events that could be included in a highlight."""
        logging.info(f"Extracting round timeline and spike events from VOD at {game.filename}.")
        round_timeline = extract_round_timeline(game)

        # TODO: If not the last game, remove the part of the VOD related to this game so it is not included in the next.

        # TODO: Run through the VOD within the rounds and find all kill events.
        logging.info(f"Extracting kill events from VOD at {game.filename}.")
        add_kill_events(game, round_timeline)

        return round_timeline

    def combine_events(self, game: GameVod, events: dict[int, SecondData]) -> None:
        """Combine multiple events happening in close succession together to create highlights."""
        # TODO: Group the events in the data into rounds.
        # TODO: Group the events within each round and create highlights.
        # TODO: For each group of events, get the value of the group.
        # TODO: Create a highlight object for each group of events.
        pass


def extract_round_timeline(game: GameVod) -> dict[int, SecondData]:
    """Parse through the VOD to find the round number, round timer, and spike events for each second of the game."""
    round_timeline = {}

    return round_timeline


def add_kill_events(game: GameVod, round_timeline: dict[int, SecondData]) -> None:
    """Check for kill events for each second in the round timeline and add the new events to the data."""
    pass
