from pathlib import Path

from demoparser import DemoParser

from highlights.highlighters.highlighter import Highlighter
from highlights.types import Event
from scrapers.models import GameVod


class CounterStrikeHighlighter(Highlighter):
    """Highlighter that uses GOTV demos to extract highlights from Counter-Strike matches."""

    def extract_events(self, game: GameVod) -> list[Event]:
        demo_filepath = f"media/demos/{game.match.create_unique_folder_path()}/{game.gotvdemo.filename}"
        parser = DemoParser(demo_filepath)

        event_types = ["round_freeze_end", "round_end", "player_death", "bomb_planted", "bomb_defused", "bomb_exploded"]
        events = [{"name": event["event_name"], "time": event["tick"] // 128}
                  for event in parser.parse_events("") if event["event_name"] in event_types]

        # Delete the GOTV demo file since it is no longer needed.
        Path(demo_filepath).unlink(missing_ok=True)

        return events

    def combine_events(self, game: GameVod, events: list[Event]) -> None:
        print(events[:10])

        # Split the events into rounds.

        # TODO: Remove player deaths that are separate from the actual highlight of the round.
        # TODO: Remove the bomb explosion if the CTs are saving and nothing happens between bomb plant and explosion.
        # TODO: Only create a highlight for the round if there are more than two events left after cleaning.
        pass
