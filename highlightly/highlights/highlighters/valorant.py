from highlights.highlighters.highlighter import Highlighter
from highlights.types import Event
from scrapers.models import GameVod


class ValorantHighlighter(Highlighter):
    """Highlighter that uses OpenCV to extract highlights from Valorant matches."""

    def extract_events(self, game: GameVod) -> list[Event]:
        """Parse through the match to find all significant events that could be included in a highlight."""
        pass

    def combine_events(self, game: GameVod, events: list[Event]) -> None:
        """Combine multiple events happening in close succession together to create highlights."""
        pass
