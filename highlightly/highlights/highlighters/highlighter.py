import logging

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
        logging.info(f"Creating highlights for {match}.")

        for game in match.gamevod_set.all():
            logging.info(f"Creating highlights for {game}.")

            events = self.extract_events(game)
            logging.info(f"Found {len(events)} events for {game}.")

            self.combine_events(game, events)
            logging.info(f"Combined {len(events)} events for {game} into {game.highlight_set.count()} highlights.")

        logging.info(f"{match} is fully highlighted and ready for further processing.")

        match.highlighted = True
        match.save(update_fields=["highlighted"])
