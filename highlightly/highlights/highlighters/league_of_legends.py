from highlights.highlighters.highlighter import Highlighter
from highlights.types import Event
from scrapers.models import GameVod


class LeagueOfLegendsHighlighter(Highlighter):
    """Highlighter that uses the LoL Esports match live view to extract highlights from League of Legends matches."""

    def extract_events(self, game: GameVod) -> list[Event]:
        pass

    def combine_events(self, game: GameVod, events: list[Event]) -> None:
        pass
