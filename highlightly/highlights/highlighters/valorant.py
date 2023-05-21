import logging
import re
import subprocess
from collections import OrderedDict
from datetime import timedelta
from multiprocessing import Pool

import cv2

from highlights.highlighters.highlighter import Highlighter
from highlights.types import SecondData
from scrapers.models import GameVod
from videos.editors.editor import get_video_length, get_video_frame_rate


class ValorantHighlighter(Highlighter):
    """Highlighter that uses PaddleOCR to extract highlights from Valorant matches."""

    def extract_events(self, game: GameVod) -> list[dict]:
        """Parse through the match to find all significant events that could be included in a highlight."""
        vod_filepath = f"{game.match.create_unique_folder_path('vods')}/{game.filename}"
        video_capture = cv2.VideoCapture(vod_filepath)
        frame_rate = get_video_frame_rate(vod_filepath)

        logging.info(f"Extracting round timeline from VOD at {game.filename} for {game}.")
        rounds = extract_round_timeline(game, vod_filepath, frame_rate)
        add_frames_to_check(rounds)

        logging.info(f"Finding spike and kill events for {game}.")
        for round, round_data in rounds.items():
            folder_path = game.match.create_unique_folder_path(f"rounds/round_{round}")
            add_spike_events(round_data, video_capture, frame_rate, folder_path)
            add_kill_events(round_data, video_capture, frame_rate, folder_path)

        # TODO: If not the last game, remove the part of the VOD related to this game so it is not included in the next.

        return rounds

    def combine_events(self, game: GameVod, events: dict[int, SecondData]) -> None:
        """Combine multiple events happening in close succession together to create highlights."""
        # TODO: Group the events within each round and create highlights.
        # TODO: For each group of events, get the value of the group.
        # TODO: Create a highlight object for each group of events.
        pass


def extract_round_timeline(game: GameVod, vod_filepath: str, frame_rate: float) -> dict[int, dict]:
    """Parse through the VOD to find each round in the game."""
    folder_path = game.match.create_unique_folder_path("frames")
    grouped_frames = get_grouped_frames(vod_filepath)

    # Save the frames that should be analyzed to disk.
    with Pool(len(grouped_frames)) as p:
        p.starmap(save_video_frames, [(vod_filepath, group, folder_path, frame_rate) for group in grouped_frames])

    # Perform optical character recognition on the saved frames to find potential text.
    frame_detections = optical_character_recognition(folder_path)

    round_timeline = create_initial_round_timeline(frame_detections)
    fill_in_round_timeline_gaps(round_timeline)
    rounds = split_timeline_into_rounds(round_timeline)

    return rounds


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
        save_round_timer_image(video_capture, frame_rate, frame_second, f"{folder_path}/{frame_second}.png")


def scale_image(image: any, scale_percent) -> any:
    """Scale the given image while keeping the aspect ratio."""
    width = int(image.shape[1] * scale_percent / 100)
    height = int(image.shape[0] * scale_percent / 100)

    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)


def create_initial_round_timeline(frame_detections: dict[int, list[str]]) -> dict[int, SecondData]:
    """Use the detections to create the initial round timeline with gaps."""
    round_timeline = {}
    round_strings = ["ROUND", "RDUND", "RDUNO", "ROVND", "ROUVND", "ROVNO", "ROUNO", "R0UND", "ROUN0"]
    most_recent_number = None

    # Use the detections to create the initial round timeline with gaps.
    for frame_second, detections in frame_detections.items():
        second_data = {}

        if len(detections) >= 1 and any(round_string in detections[0] for round_string in round_strings):
            round_numbers = re.findall(r'\d+', detections[0])

            if most_recent_number:
                round_numbers = handle_round_detection_errors(most_recent_number, detections[0], round_numbers)

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

    if "R0UND" in round:
        round_numbers.remove("0")

    most_recent_digits = list(str(most_recent_number))
    if most_recent_number >= 10 and "." in round:
        number = f"{most_recent_digits[0]}.{most_recent_digits[1]}"
        if round == f"ROUND {number}" or round == f"R0UND {number}":
            round_numbers = [most_recent_number]

    if most_recent_number >= 20:
        if round == f"ROUND Z{most_recent_digits[1]}" or round == f"ROUND 1{most_recent_digits[1]}":
            round_numbers = [most_recent_number]
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


def split_timeline_into_rounds(round_timeline: dict[int, SecondData]) -> dict[int, dict]:
    """Split the given round timeline into rounds and find the starting point and estimated end point of each round."""
    rounds = OrderedDict()
    current_round = 1
    current_round_timeline = []
    sorted_timeline = dict(sorted(round_timeline.items()))

    # Split the timeline into rounds.
    for second, second_data in sorted_timeline.items():
        if "round_number" in second_data:
            data = {"second": second, "round_time_left": second_data.get("round_time_left")}

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
    for count, (round, timeline) in enumerate(rounds.items()):
        first_live_frame = get_first_frame_in_round(timeline)
        start_time = first_live_frame["second"] - (100 - first_live_frame["round_time_left"])

        # We can only estimate the end time since there could be pauses between rounds.
        if count + 1 == len(rounds.keys()):
            estimated_end_time = timeline[-1]["second"] + 30
        else:
            next_round_timeline = list(rounds.values())[count + 1]
            next_first_live_frame = get_first_frame_in_round(next_round_timeline)

            length = 145 if count + 1 == 12 else 130
            estimated_end_time = next_first_live_frame["second"] - (length - next_first_live_frame["round_time_left"])

        rounds[round] = {"start_time": start_time, "estimated_end_time": estimated_end_time, "timeline": timeline}

    return rounds


def get_first_frame_in_round(timeline: list[dict]) -> dict:
    """Get the first live frame in the given timeline."""
    return [f for f in timeline if f["round_time_left"] is not None and f["round_time_left"] > 30][0]


def add_frames_to_check(rounds: dict) -> None:
    """Add the frames that should be checked for spike events and kills events to each round."""
    for round, round_data in rounds.items():
        # Find the frames where the spike is planted.
        timeline_without_leading_none = round_data["timeline"]
        while timeline_without_leading_none[0]["round_time_left"] is None:
            del timeline_without_leading_none[0]

        spike_planted_frames = [frame for frame in timeline_without_leading_none if frame["round_time_left"] is None]

        frames_to_check_for_spike_planted = []
        frames_to_check_for_spike_stopped = []

        # Find the frames that should be checked for the spike being planted and being defused/exploding/stopping.
        if len(spike_planted_frames) > 0:
            spike_planted_start = spike_planted_frames[0]["second"]
            frames_to_check_for_spike_planted = list(range(spike_planted_start - 9, spike_planted_start))

            spike_planted_end = spike_planted_frames[-1]["second"]
            frames_to_check_for_spike_stopped = list(range(spike_planted_end + 1, spike_planted_end + 10))

        # Find the frames that should be checked for kills.
        frames_to_check_for_kills = list(range(round_data["start_time"] + 1, round_data["estimated_end_time"]))

        round_data.update({"frames_to_check_for_spike_planted": frames_to_check_for_spike_planted,
                           "frames_to_check_for_spike_stopped": frames_to_check_for_spike_stopped,
                           "frames_to_check_for_kills": frames_to_check_for_kills})


def add_spike_events(round_data: dict, video_capture, frame_rate: float, folder_path: str) -> None:
    """Check the seconds for spike events and add each found event to the round."""
    for frame_second in round_data["frames_to_check_for_spike_planted"]:
        save_round_timer_image(video_capture, frame_rate, frame_second, f"{folder_path}/{frame_second}.png")


def add_kill_events(round_data: dict, video_capture, frame_rate: float, folder_path: str) -> None:
    """Check the seconds for kill events and add each found event to the round."""
    pass


def save_round_timer_image(video_capture, frame_rate: float, frame_second: int, file_path: str):
    """Save an image that contains the round number and timer in the given second of the given video capture."""
    video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_rate * frame_second)
    _res, frame = video_capture.read()

    if frame is not None:
        cropped_frame = frame[0:70, 910:1010]
        cv2.imwrite(file_path, scale_image(cropped_frame, 300))


def optical_character_recognition(path: str) -> str:
    """Perform optical character recognition on the given image/images using PaddleOCR."""
    cmd = f"paddleocr --image_dir {path} --use_angle_cls false --lang en --use_gpu false --enable_mkldnn true " \
          f"--use_mp true --show_log false --use_dilation true"

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

    # For each analyzed frame, save the detections in the frame.
    frame_detections = {}
    for detection in result.stdout.decode().split(f"**********{path}/"):
        split_detection = detection.replace("**********", "").split("\n")
        frame_second: str = split_detection[0].replace('.png', '')

        if frame_second.isdigit():
            frame_detections[int(frame_second)] = re.findall(r"'(.*?)'", detection, re.DOTALL)

    return frame_detections
