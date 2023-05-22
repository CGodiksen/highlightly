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


# TODO: Maybe decrease the time between event groups and then make it possible to combine highlights later if they are both kept.
# TODO: This would remove more individual events while avoiding issues with cutting small breaks.
def group_round_events(events: list[Event], bomb_planted_event_name: str) -> list[list[Event]]:
    """Group events within a round into smaller groups based on the time between events."""
    grouped_events = [[events[0]]]
    bomb_planted = events[0]["name"] == bomb_planted_event_name

    for event in events[1:]:
        last_event = grouped_events[-1][-1]

        if not bomb_planted and event["time"] - last_event["time"] > 20:
            grouped_events.append([event])
        else:
            grouped_events[-1].append(event)

        # If the bomb has been planted, add all future events in the round to the last group.
        if event["name"] == bomb_planted_event_name:
            bomb_planted = True

    return grouped_events
