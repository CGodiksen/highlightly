from demoparser import DemoParser

from highlights.highlighters.highlighter import Highlighter
from highlights.types import Event
from scrapers.models import GameVod


class CounterStrikeHighlighter(Highlighter):
    """Highlighter that uses GOTV demos to extract highlights from Counter-Strike matches."""

    def extract_events(self, game: GameVod) -> list[Event]:
        events: list[Event] = []
        parser = DemoParser(f"media/demos/{game.match.create_unique_folder_path()}/{game.gotvdemo.filename}")

        for event_type in ["round_start", "round_end", "player_death", "bomb_planted", "bomb_defused", "bomb_exploded"]:
            new = [{"name": event_type, "time": event["tick"] // 128} for event in parser.parse_events(event_type)]
            events.extend(new)

        return events

    def combine_events(self, game: GameVod, events: list[Event]) -> None:
        # TODO: Split the events into rounds and clean the per round events to get highlights.
        pass
