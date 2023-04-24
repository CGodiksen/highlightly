from highlights.highlighters.highlighter import Highlighter
from highlights.types import Event, PlayerEvent
from scrapers.models import Match


class LeagueOfLegendsHighlighter(Highlighter):
    """Highlighter that uses the LoL Esports match live view to extract highlights from League of Legends matches."""

    def extract_events(self, match: Match) -> list[Event | PlayerEvent]:
        pass

    def combine_events(self, match: Match, events: list[Event | PlayerEvent]) -> None:
        pass
