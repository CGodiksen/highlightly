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


def scale_image(image: any, scale_percent) -> any:
    """Scale the given image while keeping the aspect ratio."""
    width = int(image.shape[1] * scale_percent / 100)
    height = int(image.shape[0] * scale_percent / 100)

    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
