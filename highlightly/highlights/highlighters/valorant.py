import logging
import re
import shutil
import subprocess
from collections import OrderedDict, defaultdict
from datetime import timedelta
from difflib import SequenceMatcher

import cv2
import requests
from bs4 import BeautifulSoup

from highlights.highlighters.highlighter import Highlighter, group_round_events
from highlights.models import Highlight
from highlights.types import SecondData, Event
from scrapers.models import GameVod
from videos.editors.editor import get_video_length, get_video_frame_rate


class ValorantHighlighter(Highlighter):
    """Highlighter that uses PaddleOCR to extract highlights from Valorant matches."""

    def extract_events(self, game: GameVod) -> dict[int, dict]:
        """Parse through the match to find all significant events that could be included in a highlight."""
        game.refresh_from_db()

        vod_filepath = f"{game.match.create_unique_folder_path('vods')}/{game.filename}"
        video_capture = cv2.VideoCapture(vod_filepath)
        frame_rate = get_video_frame_rate(vod_filepath)

        logging.info(f"Extracting round timeline from VOD at {game.filename} for {game}.")
        rounds = extract_round_timeline(game, vod_filepath, frame_rate)
        add_frames_to_check(rounds, game)

        logging.info(f"Finding spike and kill events for {game}.")
        spike_folder_path = game.match.create_unique_folder_path(f"spike")
        add_spike_events(rounds, video_capture, frame_rate, spike_folder_path)

        kills_folder_path = game.match.create_unique_folder_path(f"kills")
        add_kill_events(rounds, video_capture, frame_rate, kills_folder_path)

        # Remove the folders used to save the frames that were analyzed.
        shutil.rmtree(game.match.create_unique_folder_path("frames"))
        shutil.rmtree(game.match.create_unique_folder_path("spike"))
        shutil.rmtree(game.match.create_unique_folder_path("kills"))

        return rounds

    def combine_events(self, game: GameVod, rounds: dict[int, dict]) -> None:
        """Combine multiple events happening in close succession together to create highlights."""
        clean_rounds(rounds)

        for round, round_data in rounds.items():
            if len(round_data["events"]) > 0:
                # Group the events within each round based on time.
                grouped_events = group_round_events(round_data["events"], "spike_planted")

                # Create a highlight object for each group of events.
                for group in grouped_events:
                    # For each group of events, get the value of the group.
                    value = get_highlight_value(group, round)

                    start = group[0]["time"]
                    end = group[-1]["time"]
                    events_str = " - ".join([f"{event['name']} ({event['time']})" for event in group])

                    Highlight.objects.create(game_vod=game, start_time_seconds=start, round_number=round, value=value,
                                             duration_seconds=max(end - start, 1), events=events_str)


def extract_round_timeline(game: GameVod, vod_filepath: str, frame_rate: float) -> dict[int, dict]:
    """Parse through the VOD to find each round in the game."""
    folder_path = game.match.create_unique_folder_path("frames")
    total_seconds = get_video_length(vod_filepath)
    frames = range(0, int(total_seconds) + 1, 10)

    # Save the frames that should be analyzed to disk.
    save_video_frames(vod_filepath, frames, folder_path, frame_rate)

    # Perform optical character recognition on the saved frames to find potential text.
    frame_detections = optical_character_recognition(folder_path)
    logging.info(f"Detected text in round timer images: {dict(sorted(frame_detections.items()))}")

    round_timeline = create_initial_round_timeline(frame_detections)
    fill_in_round_timeline_gaps(round_timeline)
    logging.info(f"Converted detected text to round timeline: {dict(sorted(round_timeline.items()))}")

    rounds = split_timeline_into_rounds(round_timeline, game.team_1_round_count + game.team_2_round_count)

    return rounds


def save_video_frames(vod_filepath: str, frame_group: list[int], folder_path: str, frame_rate: float) -> None:
    """Parse through the VOD for the frames in the given group and save them to the folder path."""
    video_capture = cv2.VideoCapture(vod_filepath)

    for frame_second in frame_group:
        save_round_timer_image(video_capture, frame_rate, frame_second, f"{folder_path}/{frame_second}.png")


def scale_image(image: any, scale_percent) -> any:
    """Scale the given image while keeping the aspect ratio."""
    width = int(image.shape[1] * scale_percent / 100)
    height = int(image.shape[0] * scale_percent / 100)

    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)


def create_initial_round_timeline(frame_detections: dict[int, list[str]]) -> dict[int, SecondData]:
    """Use the detections to create the initial round timeline with gaps."""
    round_timeline = {}
    most_recent_number = None

    # Use the detections to create the initial round timeline with gaps.
    for frame_second, detections in frame_detections.items():
        second_data = {}

        if len(detections) >= 1 and SequenceMatcher(a="ROUND", b=detections[0]).ratio() > 0.35:
            round_numbers = re.findall(r'\d+', detections[0])
            round_number = int(round_numbers[-1]) if len(round_numbers) >= 1 else None

            if most_recent_number:
                round_number = handle_round_detection_errors(most_recent_number, detections[0], round_number)

            if round_number is not None:
                most_recent_number = round_number
                second_data["round_number"] = round_number

        if len(detections) == 2 and ":" in detections[1] and detections[1].replace(":", "").isdigit():
            split_timer = detections[1].split(":")
            second_data["round_time_left"] = timedelta(minutes=int(split_timer[0]), seconds=int(split_timer[1])).seconds

        if len(detections) == 2 and "." in detections[1] and detections[1].replace(".", "").isdigit():
            second_data["round_time_left"] = timedelta(seconds=int(float(detections[1]))).seconds

        round_timeline[frame_second] = second_data

    return round_timeline


def handle_round_detection_errors(most_recent_number: int, round: str, round_number: int | None) -> int | None:
    """Handle common issues with missing number in round number detection."""
    if most_recent_number == 1 and round.endswith("T"):
        round_number = 1
    elif most_recent_number in [10, 11] and round.endswith("T"):
        round_number = 11
    elif most_recent_number in [20, 21] and round.endswith("T"):
        round_number = 21
    elif most_recent_number in [1, 2] and round.endswith("Z"):
        round_number = 2
    elif most_recent_number in [11, 12] and round.endswith("Z"):
        round_number = 12
    elif most_recent_number in [21, 22] and round.endswith("Z"):
        round_number = 22
    elif most_recent_number in [4, 5] and round.endswith("S"):
        round_number = 5
    elif most_recent_number in [14, 15] and round.endswith("S"):
        round_number = 15
    elif most_recent_number in [6, 7] and round.endswith("T"):
        round_number = 7
    elif most_recent_number in [16, 17] and round.endswith("T"):
        round_number = 17
    elif most_recent_number in [7, 8] and (round.endswith("B") or round.endswith("0")):
        round_number = 8
    elif most_recent_number in [17, 18] and (round.endswith("B") or round.endswith("0")):
        round_number = 18

    most_recent_digits = list(str(most_recent_number))
    if most_recent_number >= 10 and "." in round:
        number = f"{most_recent_digits[0]}.{most_recent_digits[1]}"
        if number == round.split(" ")[-1]:
            round_number = most_recent_number

    if most_recent_number >= 20:
        if round.split(" ")[-1] == f"Z{most_recent_digits[1]}" or round.split(" ")[-1] == f"1{most_recent_digits[1]}":
            round_number = most_recent_number
        elif most_recent_number == 22 and (round.split(" ")[-1] == "2Z"):
            round_number = 22

    return round_number


def fill_in_round_timeline_gaps(round_timeline: dict[int, SecondData]) -> None:
    """Fill in the missing seconds and round numbers by using the surrounding text detections."""
    for frame_second, second_data in round_timeline.items():
        if "round_number" not in second_data:
            previous_second, previous = get_closest_frame_with_round_number(round_timeline, frame_second, "previous")
            next_second, next = get_closest_frame_with_round_number(round_timeline, frame_second, "next")

            # If the surrounding detections are from the same round, set the round number.
            if previous is not None and next is not None and previous["round_number"] == next["round_number"]:
                second_data["round_number"] = previous["round_number"]
            else:
                # If the difference in the time left in the round matches the difference in the frame seconds, set the round number.
                if previous is not None and "round_time_left" in second_data and "round_time_left" in previous:
                    time_left_difference = previous["round_time_left"] - second_data["round_time_left"]
                    if (frame_second - previous_second) == time_left_difference:
                        second_data["round_number"] = previous["round_number"]
                elif next is not None and "round_time_left" in second_data and "round_time_left" in next:
                    if (next_second - frame_second) == (second_data["round_time_left"] - next["round_time_left"]):
                        second_data["round_number"] = next["round_number"]

        # If the difference in the time left between the previous and next frame matches, set the time left of the frame.
        if "round_time_left" not in second_data:
            previous_frame = round_timeline.get(frame_second - 10, None)
            next_frame = round_timeline.get(frame_second + 10, None)

            if previous_frame is not None and next_frame is not None:
                if previous_frame.get("round_number") == next_frame.get("round_number", 999):
                    if previous_frame.get("round_time_left") == next_frame.get("round_time_left", 999) + 20:
                        second_data["round_time_left"] = previous_frame["round_time_left"] - 10


def get_closest_frame_with_round_number(round_timeline: dict[int, SecondData], frame_second: int,
                                        direction: str) -> tuple[int, SecondData] | tuple[None, None]:
    """Return the closest frame with a round number to the given frame in the given direction."""
    current_frame_second = frame_second

    while 0 < current_frame_second < max(round_timeline.keys()):
        current_frame_second = current_frame_second - 10 if direction == "previous" else current_frame_second + 10
        closest_frame = round_timeline.get(current_frame_second, {})

        if "round_number" in closest_frame:
            return current_frame_second, closest_frame

    return None, None


def split_timeline_into_rounds(round_timeline: dict[int, SecondData], round_count: int) -> dict[int, dict]:
    """Split the given round timeline into rounds and find the starting point and estimated end point of each round."""
    rounds = OrderedDict()
    sorted_timeline = dict(sorted(round_timeline.items()))

    current_round = 1
    current_round_timeline = []
    first_round_found = False

    # Split the timeline into rounds.
    for second, second_data in sorted_timeline.items():
        if "round_number" in second_data:
            data = {"second": second, "round_time_left": second_data.get("round_time_left")}

            if second_data["round_number"] == current_round:
                current_round_timeline.append(data)
                first_round_found = True
            elif second_data["round_number"] == current_round + 1 and first_round_found:
                rounds[current_round] = current_round_timeline
                current_round += 1
                # TODO: Test if this causes issues.
                current_round_timeline = [data]
            elif second_data["round_number"] == 1 and current_round == round_count:
                # If reaching round 1 again we break to avoid adding events from the potentially next game in the VOD.
                rounds[current_round] = current_round_timeline
                current_round_timeline = []
                break

    # Add the final round to the rounds if it was not already added when reaching round 1 again.
    if len(current_round_timeline) > 0:
        rounds[current_round] = current_round_timeline

    # Find the starting point and estimated end point of each round.
    for count, (round, timeline) in enumerate(rounds.items()):
        logging.info(f"Finding starting point and estimated end point of round {round} using timeline: {timeline}")

        first_live_frame = get_first_frame_in_round(timeline)
        start_time = first_live_frame["second"] - (100 - first_live_frame["round_time_left"])

        # We can only estimate the end time since there could be pauses between rounds.
        if count + 1 == round_count:
            estimated_end_time = timeline[-1]["second"] + 15
        else:
            next_round_timeline = list(rounds.values())[count + 1]
            next_first_live_frame = get_first_frame_in_round(next_round_timeline)

            length = 145 if count + 1 == 12 or (count + 1 == 24 and round_count > 24) else 130
            estimated_end_time = next_first_live_frame["second"] - (length - next_first_live_frame["round_time_left"])

            # Limit the end time since there might be a long halftime pause, technical pauses, or timeouts.
            estimated_end_time = min(timeline[-1]["second"] + 10, estimated_end_time)

        rounds[round] = {"start_time": start_time, "estimated_end_time": estimated_end_time, "timeline": timeline,
                         "events": []}

    return rounds


def get_first_frame_in_round(timeline: list[dict]) -> dict:
    """Get the first live frame in the given timeline."""
    return [f for f in timeline if f["round_time_left"] is not None and f["round_time_left"] > 45][0]


def add_frames_to_check(rounds: dict, game: GameVod) -> None:
    """Add the frames that should be checked for spike events and kills events to each round."""
    round_spike_info = get_round_spike_info(game)

    for round, round_data in rounds.items():
        # Find the frames where the spike is planted.
        live_frames = [frame for frame in round_data["timeline"] if frame["second"] > round_data["start_time"]]
        spike_planted_frames = [frame for frame in live_frames if frame["round_time_left"] is None]

        frames_to_check_for_spike_planted = []
        frames_to_check_for_spike_stopped = []

        # Find the frames that should be checked for the spike being planted and being defused/exploding.
        if len(spike_planted_frames) > 0:
            spike_planted_start = spike_planted_frames[0]["second"]
            frames_to_check_for_spike_planted = list(range(spike_planted_start - 9, spike_planted_start))

            if round in round_spike_info["spike_defused"] or round in round_spike_info["spike_exploded"]:
                spike_planted_end = spike_planted_frames[-1]["second"]
                frames_to_check_for_spike_stopped = list(range(spike_planted_end + 1, spike_planted_end + 10))

        # Find the frames that should be checked for kills. If it is the last round, check more frequently to ensure
        # kills that happen when the game is finished and the broadcast cuts to the players are also included.
        start = round_data["start_time"] + 1
        end = round_data["estimated_end_time"]

        if max(rounds.keys()) == round:
            frames_to_check_for_kills = list(range(start, end))
        else:
            frames_to_check_for_kills = list(range(start, end, 2))

        round_data.update({"frames_to_check_for_spike_planted": frames_to_check_for_spike_planted,
                           "frames_to_check_for_spike_stopped": frames_to_check_for_spike_stopped,
                           "frames_to_check_for_kills": frames_to_check_for_kills})


def get_round_spike_info(game: GameVod) -> dict:
    """Return a dict with a list of rounds where the spike was defused and a list of rounds where the spike exploded."""
    round_spike_info = {"spike_defused": [], "spike_exploded": []}

    html = requests.get(url=game.match.url).text
    soup = BeautifulSoup(html, "html.parser")

    game_map = next(map for map in soup.findAll("div", class_="map") if game.map in map.text)
    game_statistics = game_map.parent.parent
    round_results = game_statistics.findAll("div", class_="vlr-rounds-row-col")

    for round_result in round_results:
        round_number_div = round_result.find("div", class_="rnd-num")
        round_image_img = round_result.find("img")

        if round_number_div is not None and round_image_img is not None:
            round_number = int(round_number_div.text)

            if "defuse" in round_image_img["src"]:
                round_spike_info["spike_defused"].append(round_number)
            elif "boom" in round_image_img["src"]:
                round_spike_info["spike_exploded"].append(round_number)

    return round_spike_info


def add_spike_events(rounds: dict[int, dict], video_capture, frame_rate: float, folder_path: str) -> None:
    """Check the seconds for spike events and add each found event to the round."""
    # Extract the round and timer for each frame to check.
    for round, data in rounds.items():
        for frame_second in data["frames_to_check_for_spike_planted"] + data["frames_to_check_for_spike_stopped"]:
            file_path = f"{folder_path}/{frame_second}.png"
            save_round_timer_image(video_capture, frame_rate, frame_second, file_path)

    # Find the round number and timer in each image.
    frame_detections = optical_character_recognition(folder_path)
    spike_round_timeline = create_initial_round_timeline(frame_detections)
    fill_in_round_timeline_gaps(spike_round_timeline)

    for round, data in rounds.items():
        # Add a spike planted event on the exact second the timer is no longer visible.
        frames_to_check_for_planted = data["frames_to_check_for_spike_planted"]
        for count, frame_second in enumerate(frames_to_check_for_planted):
            if "round_time_left" not in spike_round_timeline[frame_second]:
                data["events"].append({"name": "spike_planted", "time": frame_second})
                break

            if count + 1 == len(frames_to_check_for_planted):
                data["events"].append({"name": "spike_planted", "time": frames_to_check_for_planted[-1] + 1})

        # Add a spike stopped event on the exact second the timer is visible again.
        frames_to_check_for_stopped = data["frames_to_check_for_spike_stopped"]
        for count, frame_second in enumerate(frames_to_check_for_stopped):
            frame = spike_round_timeline[frame_second]
            if "round_time_left" in frame or "round_number" not in frame:
                data["events"].append({"name": "spike_stopped", "time": frame_second})
                break

            if count + 1 == len(frames_to_check_for_stopped):
                data["events"].append({"name": "spike_stopped", "time": frames_to_check_for_stopped[-1] + 1})


def add_kill_events(rounds: dict[int, dict], video_capture, frame_rate: float, folder_path: str) -> None:
    """Check the seconds for kill events and add each found event to the round."""
    # Extract the kill feed for each frame to check.
    for round, data in rounds.items():
        for frame_second in data["frames_to_check_for_kills"]:
            file_path = f"{folder_path}/{frame_second}.png"

            video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_rate * frame_second)
            _res, frame = video_capture.read()

            if frame is not None:
                cropped_frame = frame[75:350, 1340:1840]
                cv2.imwrite(file_path, scale_image(cropped_frame, 200))

    frame_detections = optical_character_recognition(folder_path)

    # Use the text detections to create kill events.
    events = defaultdict(list)
    for frame_second, detections in frame_detections.items():
        detections = [det for det in detections if len(det) > 3]
        recent_kills = events.get(frame_second - 2, []) + events.get(frame_second - 4, [])
        recent_kills = [kill["info"] for kill in recent_kills]

        # Group the detections into kills and add an event for each new kill.
        if len(detections) >= 2 and len(detections) % 2 == 0:
            kills = zip(*(iter(detections),) * 2)

            for kill in kills:
                kill_info = f"{kill[0]} - {kill[1]}"

                if all([SequenceMatcher(a=k, b=kill_info).ratio() < 0.9 for k in recent_kills]):
                    event = {"name": "player_death", "time": frame_second, "info": kill_info}
                    events[frame_second].append(event)

    # Add the kill events to the correct rounds in the round data.
    for frame_second, frame_events in events.items():
        corresponding_round = next(round_data for round, round_data in rounds.items() if
                                   round_data["start_time"] <= frame_second <= round_data["estimated_end_time"])

        corresponding_round["events"].extend(frame_events)


def save_round_timer_image(video_capture, frame_rate: float, frame_second: int, file_path: str) -> None:
    """Save an image that contains the round number and timer in the given second of the given video capture."""
    video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_rate * frame_second)
    _res, frame = video_capture.read()

    if frame is not None:
        cropped_frame = frame[0:70, 910:1010]
        cv2.imwrite(file_path, scale_image(cropped_frame, 300))


def optical_character_recognition(path: str) -> dict:
    """Perform optical character recognition on the given image/images using PaddleOCR."""
    cmd = f"paddleocr --image_dir {path} --use_angle_cls false --lang en --use_gpu false --enable_mkldnn true " \
          f"--use_mp true --show_log false --use_dilation true --det_db_score_mode slow"

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

    # For each analyzed frame, save the detections in the frame.
    frame_detections = {}
    for detection in result.stdout.decode().split(f"**********{path}/"):
        split_detection = detection.replace("**********", "").split("\n")
        frame_second: str = split_detection[0].replace('.png', '')

        if frame_second.isdigit():
            frame_detections[int(frame_second)] = re.findall(r"'(.*?)'", detection, re.DOTALL)

    return frame_detections


def clean_rounds(rounds: dict[int, dict]) -> None:
    """For each round, sort the events in the round and remove irrelevant spike events."""
    for round, round_data in rounds.items():
        round_data["events"] = sorted(round_data["events"], key=lambda event: event["time"])

        if len(round_data["events"]) >= 2:
            events = round_data["events"]

            # Remove the spike explosion if the CTs are saving and nothing happens between spike plant and explosion.
            if events[-2]["name"] == "spike_planted" and events[-1]["name"] == "spike_stopped":
                del round_data["events"][-1]


def get_highlight_value(events: list[Event], round) -> int:
    """Return a number that signifies how "good" the highlight is based on the content and context of the events."""
    value = 0
    event_values = {"player_death": 1, "spike_planted": 2, "spike_stopped": 2}

    # Add the value of the basic events in the highlight.
    for event in events:
        value += event_values[event["name"]]

    # All scaling is applied based on the original event score to avoid scaling already scaled values further.
    original_event_value = value

    # Add context scaling based on how late in the game the highlight is.
    round_scaler = 0.01 if round <= 24 else 0.015
    value += original_event_value * (round_scaler * round)

    # TODO: Add context scaling based on how close the round is in terms of how many players are left alive on each team.
    # TODO: Add context scaling based on the economy of the teams in the round.

    return value
