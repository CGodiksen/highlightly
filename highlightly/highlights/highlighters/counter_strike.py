from pathlib import Path

from demoparser import DemoParser

from highlights.highlighters.highlighter import Highlighter
from highlights.models import Highlight
from highlights.types import Event, Round, RoundData
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

        highlights = []
        [highlights.extend(clean_round_events(round)) for round in rounds]

        for highlight in highlights:
            # Only create a highlight for the round if there are more than two events left after cleaning.
            if len(highlight["events"]) > 2:
                start = highlight["events"][0]["time"]
                end = highlight["events"][-1]["time"]
                events_str = " - ".join([f"{event['name']} ({event['time']})" for event in highlight["events"]])

                Highlight.objects.create(game_vod=game, start_time_seconds=start, duration_seconds=end - start,
                                         events=events_str, round_number=highlight["round_number"])


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


def extract_round_data(demo_parser: DemoParser) -> list[RoundData]:
    """For each round retrieve how many were alive at the end of the round and total equipment value per team."""
    round_data: list[RoundData] = []

    # Retrieve the tick data from the demo.
    tick_df: pd.DataFrame = demo_parser.parse_ticks(["team_num", "equipment_value", "round", "health"])
    tick_df = tick_df.drop_duplicates(["round", "name"])
    tick_df = tick_df[tick_df.equipment_value != 0]

    teams = tick_df["team_num"].unique()
    rounds = sorted(tick_df["round"].unique())

    # For each round, calculate how many were alive at the end of the round per team and the total team equipment value.
    for round in rounds:
        data: RoundData = {"team_1_alive": 0, "team_1_equipment_value": 0, "team_2_alive": 0, "team_2_equipment_value": 0}

        for count, team in enumerate(teams):
            team_round_rows = tick_df.loc[(tick_df["round"] == round) & (tick_df["team_num"] == team)]
            data[f"team_{count + 1}_alive"] = len(team_round_rows.loc[team_round_rows["health"] != 0])
            data[f"team_{count + 1}_equipment_value"] = team_round_rows["equipment_value"].sum()

        round_data.append(data)

    return round_data


# TODO: Remove when 4-5 players are alive on one team and 1-2 players get hunted down at the end of the round.
def clean_round_events(round: Round) -> list[dict]:
    """
    Return a list of highlights from the round where the events and breaks that would decrease the viewing
    quality of the round are removed.
    """
    grouped_events = []
    cleaned_events = [event for event in round["events"] if event["name"] != "round_freeze_end"]

    if len(cleaned_events) > 2:
        # Remove the bomb explosion if the CTs are saving and nothing happens between bomb plant and explosion.
        if cleaned_events[-2]["name"] == "bomb_planted" and cleaned_events[-1]["name"] == "bomb_exploded":
            del cleaned_events[-1]

        grouped_events = group_round_events(cleaned_events)

        # If there are 3 or more potential highlights in a round, the second can be removed if it has 2 or less player deaths.
        if len(grouped_events) >= 3:
            second_group_kills, second_group_bombs = get_event_counts(grouped_events[1])
            if second_group_kills <= 2 and second_group_bombs == 0:
                del grouped_events[1]

        # If there are 2 or more potential highlights in a round, the first can be removed if it has 3 or less player deaths.
        if len(grouped_events) >= 2:
            first_group_kills, first_group_bombs = get_event_counts(grouped_events[0])
            if first_group_kills <= 3 and first_group_bombs == 0:
                del grouped_events[0]

    return [{"round_number": round["round_number"], "events": events} for events in grouped_events]


def group_round_events(events: list[Event]) -> list[list[Event]]:
    """Group events within a round into smaller groups based on the time between events."""
    grouped_events = [[events[0]]]

    for event in events[1:]:
        last_event = grouped_events[-1][-1]
        if event["time"] - last_event["time"] > 30:
            grouped_events.append([event])
        else:
            grouped_events[-1].append(event)

    return grouped_events


def get_event_counts(events: list[Event]) -> (int, int):
    """Return how many kills and how many bomb related events there are in the given list of events."""
    kill_events = len([event for event in events if event["name"] == "player_death"])
    bomb_related_events = len([event for event in events if "bomb" in event["name"]])

    return kill_events, bomb_related_events
