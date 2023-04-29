import logging
from datetime import timedelta

import cv2
from google.cloud import vision

from scrapers.models import GameVod
from videos.editors.editor import Editor


class CounterStrikeEditor(Editor):
    """Editor to support editing Counter-Strike VODs into highlight videos and uploading them to YouTube."""

    @staticmethod
    def find_game_starting_point(game_vod: GameVod) -> int:
        detected_timer = None
        current_offset = 30
        initial_offset = 30
        max_attempts = 10

        vod_filepath = f"media/vods/{game_vod.match.create_unique_folder_path()}/{game_vod.filename}"
        video_capture = cv2.VideoCapture(vod_filepath)
        width = video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)

        # The video is 60 FPS. Jump two seconds forward each attempt.
        for i in range(60 * initial_offset, (60 * initial_offset) + (max_attempts * 120), 120):
            current_offset = i / 60
            logging.info(f"Checking for game starting point of {game_vod}, {current_offset} seconds into the VOD.")

            # Extract a single frame from the game where the round timer is potentially visible.
            video_capture.set(cv2.CAP_PROP_POS_FRAMES, i)
            _res, frame = video_capture.read()

            # Crop the frame, so it focuses on the scoreboard and the timer.
            cropped_frame = frame[0:200, (int(width / 2) - 125):(int(width / 2) + 125)]

            # Use OCR to get the characters in the image and find the timer. If not found, try again with a new frame.
            detected_text = detect_text(cv2.imencode(".png", cropped_frame)[1].tobytes())
            detected_timer = next((text for text in detected_text if ":" in text and len(text) == 4), None)

            if detected_timer is not None:
                break

        logging.info(f"Detected {detected_timer} timer {current_offset} seconds into {game_vod}.")

        # Convert the time on the timer to an offset for when the game starts compared to when the video starts.
        split_timer = detected_timer.split(":")
        seconds_left_in_round = timedelta(minutes=int(split_timer[0]), seconds=int(split_timer[1])).seconds
        seconds_since_round_started = 115 - seconds_left_in_round

        return int(current_offset - seconds_since_round_started)


def detect_text(image_content: bytes):
    """Use the Google Cloud Vision API to detect text in the given image."""
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_content)

    response = client.text_detection(image=image)
    detected_text = response.text_annotations

    return [text.description for text in detected_text]
