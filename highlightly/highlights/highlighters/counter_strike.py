import logging
from itertools import groupby

import pandas as pd
from demoparser import DemoParser

from highlights.highlighters.highlighter import Highlighter
from highlights.types import Event, RoundData
from scrapers.models import GameVod


class CounterStrikeHighlighter(Highlighter):
    """Highlighter that uses GOTV demos to extract highlights from Counter-Strike matches."""

    def __init__(self):
        self.demo_filepath: str | None = None
        self.demo_parser: DemoParser | None = None

    # TODO: Maybe remove player deaths using event information.
    def extract_events(self, game: GameVod) -> list[Event]:
        folder_path = game.match.create_unique_folder_path("demos")
        self.demo_filepath = f"{folder_path}/{game.gotvdemo.filename}"

        logging.info(f"Parsing demo file at {self.demo_filepath} to extract events.")
        self.demo_parser = DemoParser(self.demo_filepath)

        event_types = ["round_freeze_end", "round_end", "player_death", "bomb_planted", "bomb_defused", "bomb_exploded"]
        events = [{"name": event["event_name"], "time": round(event["tick"] / 128), "info": event.get("winner", None)}
                  for event in self.demo_parser.parse_events("") if event["event_name"] in event_types]

        # Remove 8 or more player deaths that happen in the same second since that is related to a technical pause.
        grouped_events = [list(v) for _, v in groupby(events, lambda event: event["time"])]
        duplicated_events = [x[0] for x in grouped_events if len(x) >= 8]
        events = [event for event in events if event not in duplicated_events]

        return events

    def combine_events(self, game: GameVod, events: list[Event]) -> None:
        rounds = split_events_into_rounds(events, self.demo_parser)
        calibrate_event_times(rounds)
        clean_rounds(rounds)

        logging.info(f"Split events for {game} into {len(rounds)} rounds.")

        split_rounds_into_highlights(rounds)
        logging.info(f"Split {len(rounds)} into {game.highlight_set.count()} highlights.")


def split_events_into_rounds(events: list[Event], demo_parser) -> list[RoundData]:
    """Parse through the events and separate them into rounds based on the "round_end" event."""
    round_data = extract_round_data(demo_parser)

    # Add the events within the round and the winner of the round to the round data.
    for count, game_round in enumerate(round_data):
        start_time = 0 if count == 0 else round_data[count - 1]["end_time"] + 5
        game_round["events"] = [event for event in events if start_time < event["time"] <= game_round["end_time"] + 5]

        round_end = next((event for event in game_round["events"][::-1] if event["name"] == "round_end"), None)
        game_round["winner"] = round_end["info"] if round_end else None

    handle_round_edge_cases(round_data)

    return round_data


def handle_round_edge_cases(rounds: list[RoundData]):
    """Handle edge cases such as rounds being replayed, technical pauses, and missing events."""
    # If there is more than one round_freeze_end -> round_end sequence. Overwrite the previous round with the first sequence.
    for count, round in enumerate(rounds):
        round_freeze_ends = [event for event in round["events"] if event["name"] == "round_freeze_end"]
        round_ends = [event for event in round["events"] if event["name"] == "round_end"]

        if len(round_freeze_ends) > 1 and len(round_ends) > 1:
            first_round_freeze_end_index = round["events"].index(round_freeze_ends[0])

            # Find the first round_end event after the first round_freeze_end event.
            first_round_end_index = round["events"].index(round_ends[-1])
            for round_end in round_ends:
                first_round_end_index = round["events"].index(round_end)

                if first_round_end_index > first_round_freeze_end_index:
                    break

            first_sequence = round["events"][first_round_freeze_end_index: first_round_end_index + 1]

            rounds[count - 1]["events"] = first_sequence
            rounds[count - 1]["end_time"] = round["events"][first_round_end_index]["time"]

            del round["events"][first_round_freeze_end_index: first_round_end_index + 1]


def calibrate_event_times(rounds: list[RoundData]):
    """Find the first round_freeze_end event and calibrate all event times based on it."""
    first_round_freeze_end = 0
    for round in rounds:
        first_round_freeze_end = next((event["time"] for event in round["events"] if event["name"] == "round_freeze_end"), None)
        if first_round_freeze_end is not None:
            break

    if first_round_freeze_end:
        for round in rounds:
            round["end_time"] -= first_round_freeze_end

            for event in round["events"]:
                event["time"] -= first_round_freeze_end


def extract_round_data(demo_parser: DemoParser) -> list[RoundData]:
    """For each round retrieve how many were alive at the end of the round and total equipment value per team."""
    round_data: list[RoundData] = []

    # Retrieve the tick data from the demo.
    tick_df: pd.DataFrame = demo_parser.parse_ticks(["team_num", "equipment_value", "round", "health"])
    tick_df = tick_df.drop_duplicates(["round", "name"])

    # Remove observer rows.
    team_counts = tick_df.drop_duplicates(["team_num", "name"]).groupby("team_num").nunique()
    non_observer_teams = team_counts[team_counts.name >= 10].index.tolist()
    tick_df = tick_df[tick_df.team_num.isin(non_observer_teams)]
    tick_df = tick_df[tick_df["round"] > 0]

    teams = tick_df["team_num"].unique()
    rounds = sorted(tick_df["round"].unique())

    # For each round, calculate how many were alive at the end of the round per team and the total team equipment value.
    for game_round in rounds:
        round_rows = tick_df.loc[tick_df["round"] == game_round]
        round_number = round_rows["round"].iloc[0]
        data: RoundData = {"number": round_number, "end_time": round(round_rows["tick"].iloc[0] / 128),
                           "teams": list(teams)}

        for team in teams:
            team_round_rows = round_rows.loc[tick_df["team_num"] == team]
            data[f"team_{team}_alive"] = len(team_round_rows.loc[team_round_rows["health"] != 0])
            data[f"team_{team}_equipment_value"] = team_round_rows["equipment_value"].sum()

        round_data.append(data)

    return round_data


def clean_rounds(rounds: list[RoundData]):
    """For each round, remove round metadata events and irrelevant non-metadata events."""
    for round in rounds:
        removed_event_types = ["round_freeze_end", "round_end"]
        round["events"] = [event for event in round["events"] if event["name"] not in removed_event_types]

        # Remove the bomb explosion if the CTs are saving and nothing happens between bomb plant and explosion.
        if round["events"][-2]["name"] == "bomb_planted" and round["events"][-1]["name"] == "bomb_exploded":
            del round["events"][-1]


def split_rounds_into_highlights(rounds: list[RoundData]):
    """
    Group events within each round to create individual highlights and assign a value to the highlight to signify
    how "good" the highlight is.
    """
    pass


def group_round_events(events: list[Event]) -> list[list[Event]]:
    """Group events within a round into smaller groups based on the time between events."""
    grouped_events = [[events[0]]]
    bomb_planted = events[0]["name"] == "bomb_planted"

    for event in events[1:]:
        last_event = grouped_events[-1][-1]

        if not bomb_planted and event["time"] - last_event["time"] > 20:
            grouped_events.append([event])
        else:
            grouped_events[-1].append(event)

        # If the bomb has been planted, add all future events in the round to the last group.
        if event["name"] == "bomb_planted":
            bomb_planted = True

    return grouped_events


def get_highlight_value() -> int:
    """Return a number that signifies how "good" the highlight is based on the content and context of the events."""
    pass
