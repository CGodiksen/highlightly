from highlights.highlighters.highlighter import Highlighter
from highlights.types import Event
from scrapers.models import GameVod


class LeagueOfLegendsHighlighter(Highlighter):
    """Highlighter that uses the PaddleOCR and template matching to extract highlights from League of Legends matches."""

    def extract_events(self, game: GameVod) -> list[Event]:
        """Use PaddleOCR and template matching to extract events from the game vod."""
        pass

    def combine_events(self, game: GameVod, events: list[Event]) -> None:
        """Combine the events based on time and create a highlight for each group of events."""
        pass
