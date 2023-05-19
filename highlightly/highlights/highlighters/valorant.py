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
    round_timeline = {}
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
    result: subprocess.CompletedProcess = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

    frame_detections = {}

    # For each analyzed frame, save the detections in the frame.
    for detection in result.stdout.decode().split(f"**********{folder_path}/"):
        split_detection = detection.replace("**********", "").split("\n")
        frame_second: str = split_detection[0].replace('.png', '')

        if frame_second.isdigit():
            frame_detections[int(frame_second)] = re.findall(r"'(.*?)'", detection, re.DOTALL)

    initial_round_timeline = create_initial_round_timeline(frame_detections)
    print(initial_round_timeline)

    # TODO: Fill in the missing seconds by using the surrounding text detections.
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
    round_strings = ["ROUND", "RDUND", "RDUNO", "ROVND", "ROUVND"]

    # Use the detections to create the initial round timeline with gaps.
    for frame_second, detections in frame_detections.items():
        second_data = {}

        if len(detections) >= 1 and any(round_string in detections[0] for round_string in round_strings):
            round_numbers = re.findall(r'\d+', detections[0])
            if len(round_numbers) >= 1:
                second_data["round_number"] = int(round_numbers[0])

        if len(detections) == 2 and ":" in detections[1]:
            split_timer = detections[1].split(":")
            second_data["round_time_left"] = timedelta(minutes=int(split_timer[0]), seconds=int(split_timer[1])).seconds

        if len(detections) == 2 and "." in detections[1]:
            second_data["round_time_left"] = timedelta(seconds=int(float(detections[1]))).seconds

        round_timeline[frame_second] = second_data

    return round_timeline


def add_kill_events(game: GameVod, round_timeline: dict[int, SecondData]) -> None:
    """Check for kill events for each second in the round timeline and add the new events to the data."""
    pass
