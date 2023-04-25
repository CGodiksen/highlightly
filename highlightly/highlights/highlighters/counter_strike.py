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
        events = [{"name": event["event_name"], "time": event["tick"] // 128}
                  for event in parser.parse_events("") if event["event_name"] in event_types]

        # Delete the GOTV demo file since it is no longer needed.
        Path(demo_filepath).unlink(missing_ok=True)

        return events

    def combine_events(self, game: GameVod, events: list[Event]) -> None:
        rounds = split_events_into_rounds(events)
        cleaned_rounds = [clean_round_events(round) for round in rounds]

        for round in cleaned_rounds:
            # Only create a highlight for the round if there are more than two events left after cleaning.
            if len(round["events"]) > 2:
                start = round["events"][0]["time"] - 5
                end = round["events"][-1]["time"] + 5
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


def clean_round_events(round: Round) -> Round:
    """Return an updated round where the events that would decrease the viewing quality of the highlight are removed."""
    events = [event for event in round["events"] if event["name"] != "round_freeze_end"]
    cleaned_events = events[2:]

    if len(events) > 2:
        # Remove player deaths that are separate from the actual highlight of the round.
        for i in [1, 0]:
            if events[i]["name"] != "player_death" or cleaned_events[0]["time"] - events[i]["time"] <= 20:
                cleaned_events.insert(0, events[i])

        # Remove the bomb explosion if the CTs are saving and nothing happens between bomb plant and explosion.
        if cleaned_events[-2]["name"] == "bomb_planted" and cleaned_events[-1]["name"] == "bomb_exploded":
            del cleaned_events[-1]

    return {"round_number": round["round_number"], "events": cleaned_events}
