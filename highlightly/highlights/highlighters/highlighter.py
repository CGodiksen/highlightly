from highlights.types import PlayerEvent, Event
from scrapers.models import Match


class Highlighter:
    def extract_events(self, match: Match) -> list[Event | PlayerEvent]:
        """Parse through the match to find all significant events that could be included in a highlight."""
        raise NotImplementedError

    def combine_events(self, match: Match, events: list[Event | PlayerEvent]) -> None:
        """Combine multiple events happening in close succession together to create highlights."""
        raise NotImplementedError

    def highlight(self, match: Match) -> None:
        """Extract events from the match and combine events to find match highlights."""
        events = self.extract_events(match)
        self.combine_events(match, events)
