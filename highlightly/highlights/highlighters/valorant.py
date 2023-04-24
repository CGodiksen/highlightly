from highlights.highlighters.highlighter import Highlighter
from highlights.types import Event, PlayerEvent
from scrapers.models import Match


class ValorantHighlighter(Highlighter):
    """Highlighter that uses OpenCV to extract highlights from Valorant matches."""

    def extract_events(self, match: Match) -> list[Event | PlayerEvent]:
        pass

    def combine_events(self, match: Match, events: list[Event | PlayerEvent]) -> None:
        pass
