import logging
from itertools import groupby

import pandas as pd
from demoparser import DemoParser

from highlights.highlighters.highlighter import Highlighter
from highlights.models import Highlight
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
        events = [{"name": event["event_name"], "time": event["tick"], "info": event.get("winner", None)}
                  for event in self.demo_parser.parse_events("") if event["event_name"] in event_types]

        # Remove 8 or more player deaths that happen in the same second since that is related to a technical pause.
        grouped_events = [list(v) for _, v in groupby(events, lambda event: event["time"])]
        duplicated_events = [x[0] for x in grouped_events if len(x) >= 8]
        events = [event for event in events if event not in duplicated_events]

        # Check the tick data to ensure that player deaths that are not missing in the game events are included.
        kill_df = self.demo_parser.parse_ticks(["round", "kills"])
        kill_df = kill_df.drop_duplicates(["kills", "name"])[kill_df["tick"] > 128]

        new_deaths = []
        existing_deaths = [event["time"] for event in events if event["name"] == "player_death"]
        for death in kill_df["tick"].tolist():
            # If there is more than 100 ticks to the closest existing death, we count it is a new death.
            if abs(min(existing_deaths, key=lambda x: abs(x - death)) - death) > 100:
                events.append({"name": "player_death", "time": death, "info": None})
                new_deaths.append(death)

        logging.info(f"Found {len(new_deaths)} new deaths in the tick data that were not included in the game events.")

        # Convert the tick time to seconds.
        for event in events:
            event["time"] = round(event["time"] / 128)

        return events

    def combine_events(self, game: GameVod, events: list[Event]) -> None:
        rounds = split_events_into_rounds(events, self.demo_parser)
        calibrate_event_times(rounds)
        clean_rounds(rounds)

        logging.info(f"Split events for {game} into {len(rounds)} rounds.")

        split_rounds_into_highlights(rounds, game)
        logging.info(f"Split {len(rounds)} rounds into {game.highlight_set.count()} highlights.")


def split_events_into_rounds(events: list[Event], demo_parser) -> list[RoundData]:
    """Parse through the events and separate them into rounds based on the tick round data."""
    round_data = extract_round_data(demo_parser)

    # Add the events within the round and the winner of the round to the round data.
    for count, game_round in enumerate(round_data):
        # TODO: Test that 10 fixes the problem with single missed kills in the end of rounds.
        start_time = 0 if count == 0 else round_data[count - 1]["end_time"] + 10
        game_round["events"] = [event for event in events if start_time < event["time"] <= game_round["end_time"] + 10]

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
        event_types_to_remove = ["round_freeze_end", "round_end"]
        round["events"] = [event for event in round["events"] if event["name"] not in event_types_to_remove and event["time"] > 0]

        if len(round["events"]) >= 2:
            # Remove the bomb explosion if the CTs are saving and nothing happens between bomb plant and explosion.
            if round["events"][-2]["name"] == "bomb_planted" and round["events"][-1]["name"] == "bomb_exploded":
                del round["events"][-1]


def split_rounds_into_highlights(rounds: list[RoundData], game: GameVod):
    """
    Group events within each round to create individual highlights and assign a value to the highlight to signify
    how "good" the highlight is.
    """
    for round in rounds:
        if len(round["events"]) > 0:
            grouped_events = group_round_events(round["events"])

            for group in grouped_events:
                value = get_highlight_value(group, round)

                start = group[0]["time"]
                end = group[-1]["time"]
                events_str = " - ".join([f"{event['name']} ({event['time']})" for event in group])

                Highlight.objects.create(game_vod=game, start_time_seconds=start, duration_seconds=max(end - start, 1),
                                         events=events_str, round_number=round["number"], value=value)


# TODO: Maybe decrease the time between event groups and then make it possible to combine highlights later if they are both kept.
# TODO: This would remove more individual events while avoiding issues with cutting small breaks.
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


def get_highlight_value(events: list[Event], round: RoundData) -> int:
    """Return a number that signifies how "good" the highlight is based on the content and context of the events."""
    value = 0
    teams = round["teams"]
    event_values = {"player_death": 1, "bomb_planted": 2, "bomb_defused": 2, "bomb_exploded": 1}

    # Add the value of the basic events in the highlight.
    for event in events:
        value += event_values[event["name"]]

    # All scaling is applied based on the original event score to avoid scaling already scaled values further.
    original_event_value = value

    # Add context scaling based on how late in the game the highlight is.
    round_scaler = 0.01 if round["number"] <= 30 else 0.015
    value += original_event_value * (round_scaler * round["number"])

    # Add context scaling based on how close the round is in terms of how many players are left alive on each team.
    player_alive_difference = abs(round[f"team_{teams[0]}_alive"] - round[f"team_{teams[1]}_alive"])
    value += original_event_value * (0.5 - (player_alive_difference * 0.1))

    # Add context scaling based on the economy of the teams in the round. The winning team having better
    # equipment scales the value down and the losing team having better equipment scales the value up.
    if round["winner"] is not None and f"team_{round['winner']}_equipment_value" in round:
        winning_team_equipment = round[f"team_{round['winner']}_equipment_value"]
        losing_team = next(team for team in teams if team != round["winner"])
        losing_team_equipment = round[f"team_{losing_team}_equipment_value"]

        buy_level_difference = get_buy_level(winning_team_equipment) - get_buy_level(losing_team_equipment)
        value += original_event_value * (buy_level_difference * 0.25)

    return value


def get_buy_level(equipment_value: int) -> int:
    if equipment_value >= 20000:
        return 0  # Full buy.
    elif equipment_value >= 10000:
        return 1 # Half buy.
    else:
        return 2 # Eco.
