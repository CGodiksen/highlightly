from highlights.highlighters.highlighter import Highlighter
from highlights.types import Event
from scrapers.models import GameVod


class ValorantHighlighter(Highlighter):
    """Highlighter that uses OpenCV to extract highlights from Valorant matches."""

    def extract_events(self, game: GameVod) -> list[Event]:
        pass

    def combine_events(self, game: GameVod, events: list[Event]) -> None:
        pass
