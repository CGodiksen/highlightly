from highlights.types import Event
from scrapers.models import Match, GameVod


class Highlighter:
    def extract_events(self, game: GameVod) -> list[Event]:
        """Parse through the match to find all significant events that could be included in a highlight."""
        raise NotImplementedError

    def combine_events(self, game: GameVod, events: list[Event]) -> None:
        """Combine multiple events happening in close succession together to create highlights."""
        raise NotImplementedError

    def highlight(self, match: Match) -> None:
        """Extract events from the match and combine events to find match highlights."""
        for game in match.gamevod_set.all():
            events = self.extract_events(game)
            self.combine_events(game, events)

        match.highlighted = True
        match.save(update_fields=["highlighted"])
