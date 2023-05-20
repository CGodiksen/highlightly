import logging
import re
import subprocess
from datetime import timedelta
from multiprocessing import Pool

import cv2

from highlights.highlighters.highlighter import Highlighter
from highlights.types import SecondData
from scrapers.models import GameVod
from videos.editors.editor import get_video_length, get_video_frame_rate


class ValorantHighlighter(Highlighter):
    """Highlighter that uses PaddleOCR to extract highlights from Valorant matches."""

    def extract_events(self, game: GameVod) -> dict[int, SecondData]:
        """Parse through the match to find all significant events that could be included in a highlight."""
        logging.info(f"Extracting round timeline and spike events from VOD at {game.filename}.")
        round_timeline = extract_round_timeline(game)

        # TODO: If not the last game, remove the part of the VOD related to this game so it is not included in the next.

        # TODO: Run through the VOD within the rounds and find all kill events.
        logging.info(f"Extracting kill events from VOD at {game.filename}.")
        add_kill_events(game, round_timeline)

        return round_timeline

    def combine_events(self, game: GameVod, events: dict[int, SecondData]) -> None:
        """Combine multiple events happening in close succession together to create highlights."""
        # TODO: Group the events in the data into rounds.
        # TODO: Group the events within each round and create highlights.
        # TODO: For each group of events, get the value of the group.
        # TODO: Create a highlight object for each group of events.
        pass


def extract_round_timeline(game: GameVod) -> dict[int, SecondData]:
    """Parse through the VOD to find the round number, round timer, and spike events for each second of the game."""
    vod_filepath = f"{game.match.create_unique_folder_path('vods')}/{game.filename}"
    folder_path = game.match.create_unique_folder_path("frames")

    grouped_frames = get_grouped_frames(vod_filepath)
    frame_rate = get_video_frame_rate(vod_filepath)

    # Save the frames that should be analyzed to disk.
    with Pool(len(grouped_frames)) as p:
        p.starmap(save_video_frames, [(vod_filepath, group, folder_path, frame_rate) for group in grouped_frames])

    # Perform optical character recognition on the saved frames to find potential text.
    cmd = f"paddleocr --image_dir {folder_path} --use_angle_cls false --lang en --use_gpu false --enable_mkldnn true " \
          f"--use_mp true --show_log false"
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

    # For each analyzed frame, save the detections in the frame.
    frame_detections = {}
    for detection in result.stdout.decode().split(f"**********{folder_path}/"):
        split_detection = detection.replace("**********", "").split("\n")
        frame_second: str = split_detection[0].replace('.png', '')

        if frame_second.isdigit():
            frame_detections[int(frame_second)] = re.findall(r"'(.*?)'", detection, re.DOTALL)

    round_timeline = create_initial_round_timeline(frame_detections)
    fill_in_round_timeline_gaps(round_timeline)
    rounds = split_timeline_into_rounds(round_timeline, game.team_1_round_count + game.team_2_round_count)

    print(rounds)

    # TODO: Find the exact times of the spike being planted, being defused, and exploding.

    return round_timeline


def get_grouped_frames(vod_filepath: str) -> list[list[int]]:
    """Find 10-minute groups of frames that need to be extracted from the given vod filepath."""
    grouped_frames = []
    total_seconds = get_video_length(vod_filepath)

    current_second = 0
    second_limit = 0

    while second_limit <= total_seconds:
        second_limit += 600
        grouped_frames.append([])

        for i in range(current_second, min(int(total_seconds), second_limit) + 1, 10):
            grouped_frames[-1].append(current_second)
            current_second += 10

    return grouped_frames


def save_video_frames(vod_filepath: str, frame_group: list[int], folder_path: str, frame_rate: float) -> None:
    """Parse through the VOD for the frames in the given group and save them to the folder path."""
    video_capture = cv2.VideoCapture(vod_filepath)

    for frame_second in frame_group:
        video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_rate * frame_second)
        _res, frame = video_capture.read()

        if frame is not None:
            cropped_frame = frame[0:85, 910:1010]
            cv2.imwrite(f"{folder_path}/{frame_second}.png", scale_image(cropped_frame, 250))


def scale_image(image: any, scale_percent) -> any:
    """Scale the given image while keeping the aspect ratio."""
    width = int(image.shape[1] * scale_percent / 100)
    height = int(image.shape[0] * scale_percent / 100)

    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)


def create_initial_round_timeline(frame_detections: dict[int, list[str]]) -> dict[int, SecondData]:
    """Use the detections to create the initial round timeline with gaps."""
    round_timeline = {}
    round_strings = ["ROUND", "RDUND", "RDUNO", "ROVND", "ROUVND", "ROVNO", "ROUNO"]
    most_recent_number = None

    # Use the detections to create the initial round timeline with gaps.
    for frame_second, detections in frame_detections.items():
        second_data = {}

        if len(detections) >= 1 and any(round_string in detections[0] for round_string in round_strings):
            round = detections[0]
            round_numbers = re.findall(r'\d+', round)
            round_numbers = handle_round_detection_errors(most_recent_number, round, round_numbers)

            if len(round_numbers) >= 1:
                most_recent_number = int(round_numbers[0])
                second_data["round_number"] = int(round_numbers[0])

        if len(detections) == 2 and ":" in detections[1]:
            split_timer = detections[1].split(":")
            second_data["round_time_left"] = timedelta(minutes=int(split_timer[0]), seconds=int(split_timer[1])).seconds

        if len(detections) == 2 and "." in detections[1]:
            second_data["round_time_left"] = timedelta(seconds=int(float(detections[1]))).seconds

        round_timeline[frame_second] = second_data

    return round_timeline


def handle_round_detection_errors(most_recent_number: int, round: str, round_numbers: list[int]) -> list[int]:
    """Handle common issues with missing number in round number detection."""
    if most_recent_number == 1 and (round == "ROUND" or round == "ROUNDT" or round == "ROUND T" or round == "ROUNDE"):
        round_numbers = [1]
    elif most_recent_number == 7 and (round == "ROUNDT" or round == "ROUND T"):
        round_numbers = [7]
    elif most_recent_number == 8 and (round == "ROUND" or round == "ROVNOB" or round == "ROUNDB" or round == "ROUNOB"):
        round_numbers = [8]

    for i in range(0, 10):
        if most_recent_number == i + 20 and (round == f"ROUND Z{i}" or round == f"ROUND 1{i}"):
            round_numbers = [i + 20]
        elif most_recent_number == 22 and (round == "ROUND 2Z"):
            round_numbers = [22]

    return round_numbers


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
                    if (frame_second - previous_second) == (previous["round_time_left"] - second_data["round_time_left"]):
                        second_data["round_number"] = previous["round_number"]
                elif next is not None and "round_time_left" in second_data and "round_time_left" in next:
                    if (next_second - frame_second) == (second_data["round_time_left"] - next["round_time_left"]):
                        second_data["round_number"] = next["round_number"]


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


# TODO: Find the start time and estimated end time of each round.
# TODO: Find the seconds that need to be checked for the spike being planted, exploding/defused, or round ending due to last player being killed.
# TODO: Find the seconds that need to be checked for kill events.
# TODO: Check the seconds for the events and add each event to the round.

# TODO: Group the events within each round and create highlights.
# TODO: For each group of events, get the value of the group.
# TODO: Create a highlight object for each group of events.
def split_timeline_into_rounds(round_timeline: dict[int, SecondData]) -> dict:
    """Split the given round timeline into rounds and find the starting point and estimated end point of each round."""
    rounds = {}
    current_round = 1
    current_round_timeline = []
    sorted_timeline = dict(sorted(round_timeline.items()))

    # Split the timeline into rounds.
    for second, second_data in sorted_timeline.items():
        if "round_number" in second_data:
            data = {"second": second, "round_time_left": second_data.get("round_time_left", None)}

            if second_data["round_number"] == current_round:
                current_round_timeline.append(data)
            elif second_data["round_number"] == current_round + 1:
                rounds[current_round] = current_round_timeline
                current_round += 1
                current_round_timeline = []
            elif second_data["round_number"] == 1:
                # If reaching round 1 again we break to avoid adding events from the potentially next game in the VOD.
                rounds[current_round] = current_round_timeline
                break

    # Find the starting point and estimated end point of each round.
    for round, timeline in rounds.items():
        print(round)
        print(timeline)
        first_live_frame = [f for f in timeline if f["round_time_left"] is not None and f["round_time_left"] > 30][0]
        start_time = first_live_frame["second"] - (100 - first_live_frame["round_time_left"])
        print(start_time)
        print()

    return rounds


def add_kill_events(game: GameVod, round_timeline: dict[int, SecondData]) -> None:
    """Check for kill events for each second in the round timeline and add the new events to the data."""
    pass
