import logging
from collections import defaultdict
from datetime import timedelta

import cv2

from highlights.highlighters.highlighter import Highlighter
from highlights.highlighters.util import scale_image, optical_character_recognition
from highlights.types import Event
from scrapers.models import GameVod
from videos.editors.editor import get_video_frame_rate, get_video_length


class LeagueOfLegendsHighlighter(Highlighter):
    """Highlighter that uses the PaddleOCR and template matching to extract highlights from League of Legends matches."""

    # TODO: Maybe include the object kills from the graphql match data to ensure they are included.
    def extract_events(self, game_vod: GameVod) -> list[Event]:
        """Use PaddleOCR and template matching to extract events from the game vod."""
        # TODO: Handle issue with multiple games being present in a single VOD.
        # Use PaddleOCR to find the segment of the VOD that contains the live game itself.
        timeline = extract_game_timeline(game_vod)

        # Find the frames that should be checked within the live game segment.
        start_second = get_game_start_second(timeline)
        end_second = get_game_end_second(timeline)

        logging.info(f"{game_vod} starts at {start_second} and ends at {end_second} in {game_vod.filename}.")

        frames_to_check = range(start_second, end_second + 1, 4)

        # TODO: Use template matching or color thresholding to find the events within the frames.

        return []

    def combine_events(self, game: GameVod, events: list[Event]) -> None:
        """Combine the events based on time and create a highlight for each group of events."""
        pass


def extract_game_timeline(game_vod: GameVod) -> dict[int, int]:
    """
    Return the timeline of the game within the full VOD using PaddleOCR. Return it as a dict from the frame second
    to the time in the match at the frame.
    """
    logging.info(f"Extracting game timeline from VOD at {game_vod.filename} for {game_vod}.")

    vod_filepath = f"{game_vod.match.create_unique_folder_path('vods')}/{game_vod.filename}"
    video_capture = cv2.VideoCapture(vod_filepath)
    frame_rate = get_video_frame_rate(vod_filepath)

    total_seconds = get_video_length(vod_filepath)
    frames = range(0, int(total_seconds) + 1, 60)

    # Save a frame for each minute in the full VOD.
    frame_folder_path = game_vod.match.create_unique_folder_path("frames")
    for frame_second in frames:
        save_timer_image(video_capture, frame_rate, frame_second, f"{frame_folder_path}/{frame_second}.png")

    # Attempt to find the game time in each image.
    frame_detections = optical_character_recognition(frame_folder_path)
    logging.info(f"Detected text in timer images: {dict(sorted(frame_detections.items()))}")

    timeline = {}

    # Use the detections to create the timeline.
    for frame_second, detections in frame_detections.items():
        detected_timer = next((text for text in detections if ":" in text and text.replace(":", "").isdigit()), None)

        if detected_timer:
            split_timer = detected_timer.split(":")
            timeline[frame_second] = timedelta(minutes=int(split_timer[0]), seconds=int(split_timer[1])).seconds

    return timeline

def save_timer_image(video_capture, frame_rate: float, frame_second: int, file_path: str) -> None:
    """Save an image that contains the timer in the given second of the given video capture."""
    video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_rate * frame_second)
    _res, frame = video_capture.read()

    if frame is not None:
        cropped_frame = frame[0:100, 910:1010]
        cv2.imwrite(file_path, scale_image(cropped_frame, 300))


def get_game_start_second(timeline: dict[int, int]) -> int:
    """Using the given timeline, find the second that the game started on."""
    start_times = defaultdict(int)

    # For each found timer, check the start time in relation to that timer.
    for frame_second, timer in timeline.items():
        start_times[frame_second - timer] += 1

    return max(start_times, key=start_times.get)


def get_game_end_second(timeline: dict[int, int]) -> int:
    """Using the given timeline, extract frames near the end of the timeline to find the exact end second."""
    return timeline[max(timeline.keys())] + 60
