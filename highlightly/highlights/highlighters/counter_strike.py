import logging
from itertools import groupby

import pandas as pd
from demoparser import DemoParser

from highlights.highlighters.highlighter import Highlighter
from highlights.models import Highlight
from highlights.types import Event, Round, RoundData
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
        logging.info(f"Split events for {game} into {len(rounds)} rounds.")

        # TODO: For each round, remove round events, clean irrelevant non round events, and split the events in the round into highlights.
        # TODO: Assign a value to each highlight based on the calculation. Selecting which highlights should be included should be in the video editor.

        cleaned_rounds = clean_rounds(rounds, self.demo_parser)

        highlights = []
        [highlights.extend(clean_round_events(round)) for round in cleaned_rounds]

        for count, highlight in enumerate(highlights):
            # Only create a highlight for the round if there are more than two events left after cleaning, or it is the last highlight.
            if len(highlight["events"]) > 2 or count + 1 == len(highlights):
                start = highlight["events"][0]["time"]
                end = highlight["events"][-1]["time"]
                events_str = " - ".join([f"{event['name']} ({event['time']})" for event in highlight["events"]])

                Highlight.objects.create(game_vod=game, start_time_seconds=start, duration_seconds=end - start,
                                         events=events_str, round_number=highlight["round_number"])


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
    calibrate_event_times(round_data)

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


def clean_rounds(rounds: list[Round], demo_parser: DemoParser) -> list[Round]:
    """Return a cleaned list of rounds where the one-sided eco rounds have been removed."""
    cleaned_rounds = []
    round_data = extract_round_data(demo_parser)[1:]
    eco_rounds = get_eco_rounds(round_data)

    for count, round in enumerate(rounds):
        round_number = count + 1

        # If it is the last half of the round or the very last round, always keep the round.
        if round_number == 15 or round_number == len(rounds) or round_number not in eco_rounds:
            cleaned_rounds.append(round)

    return cleaned_rounds


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


def get_eco_rounds(round_data: list[RoundData]) -> list[int]:
    """
    Given a list with round data, return the round numbers of the rounds that are eco rounds where the team
    that is expected to win, wins.
    """
    eco_rounds = []

    for count, data in enumerate(round_data):
        team_1_eco = (data["team_1_equipment_value"] / 5) < 2500 and (data["team_2_equipment_value"] / 5) > 2500
        team_2_eco = (data["team_2_equipment_value"] / 5) < 2500 and (data["team_1_equipment_value"] / 5) > 2500

        team_1_eco_expected_win = team_1_eco and data["team_1_alive"] == 0 and data["team_2_alive"] >= 3
        team_2_eco_expected_win = team_2_eco and data["team_2_alive"] == 0 and data["team_1_alive"] >= 3

        if team_1_eco_expected_win or team_2_eco_expected_win:
            eco_rounds.append(count + 1)

    return eco_rounds


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

        # If there are 2 or more potential highlights in a round, the first can be removed if it has 4 or less player deaths.
        if len(grouped_events) >= 2:
            first_group_kills, first_group_bombs = get_event_counts(grouped_events[0])
            if first_group_kills <= 4 and first_group_bombs == 0:
                del grouped_events[0]

    return [{"round_number": round["round_number"], "events": events} for events in grouped_events]


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


def get_event_counts(events: list[Event]) -> (int, int):
    """Return how many kills and how many bomb related events there are in the given list of events."""
    kill_events = len([event for event in events if event["name"] == "player_death"])
    bomb_related_events = len([event for event in events if "bomb" in event["name"]])

    return kill_events, bomb_related_events
