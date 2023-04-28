from pathlib import Path

from demoparser import DemoParser

from highlights.highlighters.highlighter import Highlighter
from highlights.models import Highlight
from highlights.types import Event, Round
from scrapers.models import GameVod


class CounterStrikeHighlighter(Highlighter):
    """Highlighter that uses GOTV demos to extract highlights from Counter-Strike matches."""

    def extract_events(self, game: GameVod) -> list[Event]:
        demo_filepath = f"media/demos/{game.match.create_unique_folder_path()}/{game.gotvdemo.filename}"
        parser = DemoParser(demo_filepath)

        event_types = ["round_freeze_end", "player_death", "bomb_planted", "bomb_defused", "bomb_exploded"]
        events = [{"name": event["event_name"], "time": round(event["tick"] / 128)}
                  for event in parser.parse_events("") if event["event_name"] in event_types]

        # Delete the GOTV demo file since it is no longer needed.
        Path(demo_filepath).unlink(missing_ok=True)

        # Calibrate the event times, so they are in relation to when the first freeze time is over.
        first_start_time = next(event for event in events if event["name"] == "round_freeze_end")["time"]

        for event in events:
            event["time"] -= first_start_time

        return events

    def combine_events(self, game: GameVod, events: list[Event]) -> None:
        rounds = split_events_into_rounds(events)
        cleaned_rounds = [clean_round_events(round) for round in rounds]

        for round in cleaned_rounds:
            # Only create a highlight for the round if there are more than two events left after cleaning.
            if len(round["events"]) > 2:
                start = round["events"][0]["time"]
                end = round["events"][-1]["time"]
                events_str = " - ".join([f"{event['name']} ({event['time']})" for event in round["events"]])

                Highlight.objects.create(game_vod=game, start_time_seconds=start, duration_seconds=end - start,
                                         events=events_str, round_number=round["round_number"])


def split_events_into_rounds(events: list[Event]) -> list[Round]:
    """Parse through the events and separate them into rounds based on the "round_end" event."""
    rounds: list[Round] = []
    round_counter = 0
    round = {"round_number": round_counter, "events": []}

    for count, event in enumerate(events):
        if event["name"] == "round_freeze_end" or count == len(events) - 1:
            rounds.append(round)

            round_counter += 1
            round = {"round_number": round_counter, "events": []}
        else:
            round["events"].append(event)

    return rounds


# TODO: Remove when 4-5 players are alive on one team and 1-2 players get hunted down at the end of the round.
# TODO: Remove very one sided eco rounds if it is not one of the last two rounds in the half or in the game.
# TODO: Change it so we first set all events of a round as a potential highlight.
# TODO: Then we split on long breaks.
# TODO: Everything related to the bomb should always be included before the step where we prune CTs saving.
def clean_round_events(round: Round) -> Round:
    """Return an updated round where the events that would decrease the viewing quality of the highlight are removed."""
    cleaned_events = [event for event in round["events"] if event["name"] != "round_freeze_end"]

    if len(cleaned_events) > 2:
        # Remove the bomb explosion if the CTs are saving and nothing happens between bomb plant and explosion.
        if cleaned_events[-2]["name"] == "bomb_planted" and cleaned_events[-1]["name"] == "bomb_exploded":
            del cleaned_events[-1]

    grouped_events = group_round_events(cleaned_events)
    # TODO: If there are 2 or more potential highlights in a round, the first can be removed if it has 3 or less player deaths.
    if len(grouped_events) >= 2 and len([event for event in grouped_events[0] if event["name"] == "player_death"]) >= 3:
        pass
    # TODO: If there are 3 or more potential highlights in a round, the second can be removed if it has 2 or less player deaths.


    return {"round_number": round["round_number"], "events": cleaned_events}


def group_round_events(events: list[Event]) -> list[list[Event]]:
    """Group events within a round into smaller groups based on the time between events."""
    grouped_events = [events[0]]

    for event in events[1:]:
        last_event = grouped_events[-1][-1]
        if event["time"] - last_event["time"] > 30:
            grouped_events.append([event])
        else:
            grouped_events[-1].append(event)

    return grouped_events
