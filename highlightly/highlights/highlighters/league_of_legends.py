import logging
import shutil
from collections import defaultdict
from datetime import timedelta

import cv2
import numpy as np

from highlights.highlighters.highlighter import Highlighter, group_events
from highlights.highlighters.util import scale_image, optical_character_recognition
from highlights.models import Highlight
from highlights.types import Event
from scrapers.models import GameVod
from videos.editors.editor import get_video_frame_rate, get_video_length


class LeagueOfLegendsHighlighter(Highlighter):
    """Highlighter that uses the PaddleOCR and template matching to extract highlights from League of Legends matches."""

    def extract_events(self, game_vod: GameVod) -> list[Event]:
        """Use PaddleOCR and template matching to extract events from the game vod."""

        vod_filepath = f"{game_vod.match.create_unique_folder_path('vods')}/{game_vod.filename}"
        video_capture = cv2.VideoCapture(vod_filepath)
        frame_rate = get_video_frame_rate(vod_filepath)
        total_seconds = get_video_length(vod_filepath)

        # Use PaddleOCR to find the segment of the VOD that contains the live game itself.
        timeline = extract_game_timeline(game_vod, video_capture, frame_rate, total_seconds)
        logging.info(f"Found timeline in {game_vod}: {timeline}")

        # Find the frames that should be checked within the live game segment.
        start_second = get_game_start_second(timeline)
        end_second = get_game_end_second(game_vod, timeline, video_capture, frame_rate)

        logging.info(f"{game_vod} starts at {start_second} and ends at {end_second} in {game_vod.filename}.")

        frames_to_check = list(range(start_second, end_second + 1, 4))
        logging.info(f"Checking {len(frames_to_check)} frames for events in {game_vod}.")

        # Remove the folders used to save the frames that were analyzed.
        shutil.rmtree(game_vod.match.create_unique_folder_path("frames"))
        shutil.rmtree(game_vod.match.create_unique_folder_path("last_frames"))

        return get_game_events(game_vod, video_capture, frame_rate, frames_to_check, end_second)

    def combine_events(self, game: GameVod, events: list[Event]) -> None:
        """Combine the events based on time and create a highlight for each group of events."""
        # Group the events within each round based on time.
        grouped_events = group_events(events, "", 30)

        for group in grouped_events:
            # Create a highlight object for each group of events.
            value = get_highlight_value(group)

            start = group[0]["time"]
            end = group[-1]["time"]
            events_str = " - ".join([f"{event['name']} ({event['time']})" for event in group])

            Highlight.objects.create(game_vod=game, start_time_seconds=start, round_number=1, value=value,
                                     duration_seconds=max(end - start, 1), events=events_str)


def extract_game_timeline(game_vod: GameVod, video_capture, frame_rate: float, total_seconds: float) -> dict[int, int]:
    """
    Return the timeline of the game within the full VOD using PaddleOCR. Return it as a dict from the frame second
    to the time in the match at the frame.
    """
    logging.info(f"Extracting game timeline from VOD at {game_vod.filename} for {game_vod}.")

    frames = range(0, int(total_seconds) + 1, 20)

    # Save a frame for every 20 seconds in the full VOD.
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

        if detected_timer is not None:
            split_timer = detected_timer.split(":")
            timeline[frame_second] = timedelta(minutes=int(split_timer[0]), seconds=int(split_timer[1])).seconds

    return timeline


def save_timer_image(video_capture, frame_rate: float, frame_second: int, file_path: str) -> None:
    """Save an image that contains the timer in the given second of the given video capture."""
    video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_rate * frame_second)
    _res, frame = video_capture.read()

    if frame is not None:
        cropped_frame = frame[0:110, 910:1010]
        cv2.imwrite(file_path, scale_image(cropped_frame, 300))


def get_game_start_second(timeline: dict[int, int]) -> int:
    """Using the given timeline, find the second that the game started on."""
    start_times = defaultdict(int)

    # For each found timer, check the start time in relation to that timer.
    for frame_second, timer in timeline.items():
        start_times[frame_second - timer] += 1

    # Find each valid start time.
    valid_start_times = []
    for start_time, count in start_times.items():
        if count > 10:
            valid_start_times.append(start_time)

    return max(1, int(min(valid_start_times)))


def get_game_end_second(game_vod: GameVod, timeline: dict[int, int], video_capture, frame_rate: float) -> int:
    """Using the given timeline, extract frames near the end of the timeline to find the exact end second."""
    # TODO: Find the last element in the timeline that is related to the game.

    frames_to_check = range(max(timeline.keys()), max(timeline.keys()) + 21)
    frame_folder_path = game_vod.match.create_unique_folder_path("last_frames")

    for frame_second in frames_to_check:
        save_timer_image(video_capture, frame_rate, frame_second, f"{frame_folder_path}/{frame_second}.png")

    frame_detections = optical_character_recognition(frame_folder_path)
    logging.info(f"Detected text in timer images: {dict(sorted(frame_detections.items()))}")

    # Get the last frame second that includes a timer.
    frames_with_timer = []
    for frame_second, detections in frame_detections.items():
        detected_timer = next((text for text in detections if ":" in text and text.replace(":", "").isdigit()), None)

        if detected_timer is not None:
            frames_with_timer.append(frame_second)

    return max(frames_with_timer)


# TODO: Maybe include the object kills from the graphql match data to ensure they are included.
def get_game_events(game_vod: GameVod, video_capture, frame_rate: float, frames_to_check: list[int],
                    end_second: int) -> list[dict]:
    """Check each frame for events using template matching and return the list of found events."""
    events = []

    template_paths = get_kill_feed_templates(game_vod)
    template_images = [cv2.imread(template_path, cv2.IMREAD_GRAYSCALE) for template_path in template_paths]

    for frame_second in frames_to_check:
        video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_rate * frame_second)
        _res, frame = video_capture.read()

        # Modify the image to best capture the kill feed.
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Handle slight differences in the placement of the area with the kill feed.
        height, width = get_kill_feed_placement(game_vod)
        cropped_frame_gray = frame_gray[height[0]:height[1], width[0]:width[1]]

        # Match on the different icons that can be in the kill feed.
        mask = np.zeros(cropped_frame_gray.shape[:2], np.uint8)
        for (template_path, template_image) in zip(template_paths, template_images):
            w, h = template_image.shape[::-1]
            result = cv2.matchTemplate(cropped_frame_gray, template_image, cv2.TM_CCOEFF_NORMED)

            loc = np.where(result >= 0.8)

            for pt in zip(*loc[::-1]):
                # Check if the template match has already been found.
                if mask[pt[1] + int(round(h / 2)), pt[0] + int(round(w / 2))] != 255:
                    mask[pt[1]:pt[1] + h, pt[0]:pt[0] + w] = 255
                    events.append({"name": "event", "time": frame_second})

    # Add an event for the nexus being destroyed.
    events.append({"name": "nexus_destroyed", "time": end_second})

    return events


def get_highlight_value(events: list[Event]) -> int:
    """Return a number that signifies how "good" the highlight is based on the content and context of the events."""
    value = 0
    event_values = {"event": 1, "nexus_destroyed": 100}

    # Add the value of the basic events in the highlight.
    for event in events:
        value += event_values[event["name"]]

    return value


def get_kill_feed_placement(game_vod: GameVod) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return the height and width measurements to extract the center of the kill feed for the tournament."""
    if game_vod.match.tournament.short_name.lower() == "cblol":
        height = (480, 760)
        width = (1659, 1696)
    elif game_vod.match.tournament.short_name.lower() == "lcs":
        height = (480, 770)
        width = (1659, 1702)
    else:
        height = (480, 750)
        width = (1653, 1690)

    return height, width


def get_kill_feed_templates(game_vod: GameVod) -> list[str]:
    """Return the path to the templates of the icons that can be in the kill feed for the specific tournament."""
    if game_vod.match.tournament.short_name.lower() == "lec":
        return ["media/templates/single_sword_lec.png", "media/templates/multiple_sword_lec.png"]
    else:
        return ["media/templates/single_sword_red.png", "media/templates/multiple_sword_red.png",
                "media/templates/single_big_sword_red.png"]
