import logging

import cv2

from highlights.highlighters.highlighter import Highlighter
from highlights.types import SecondData
from scrapers.models import GameVod
from videos.editors.editor import get_video_length


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
    frame_folder_path = game.match.create_unique_folder_path("frames")
    total_seconds = get_video_length(vod_filepath)

    current_second = 0
    second_limit = 0

    # Continue parsing through the VOD in 10 minute increments until the last round is over.
    while second_limit <= total_seconds:
        second_limit += 600

        for i in range(current_second, min(int(total_seconds), second_limit) + 1, 10):
            # Save the top middle part of the frame in the current second.
            video_capture = cv2.VideoCapture(vod_filepath)
            video_capture.set(cv2.CAP_PROP_POS_FRAMES, 60 * current_second)
            _res, frame = video_capture.read()

            cropped_frame = frame[0:85, 920:1000]

            frame_filepath = f"{frame_folder_path}/{current_second}.jpg"
            cv2.imwrite(frame_filepath, cropped_frame)

            current_second += 10

    return round_timeline


def add_kill_events(game: GameVod, round_timeline: dict[int, SecondData]) -> None:
    """Check for kill events for each second in the round timeline and add the new events to the data."""
    pass
