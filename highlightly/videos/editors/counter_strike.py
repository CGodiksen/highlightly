import cv2

from scrapers.models import GameVod
from videos.editors.editor import Editor


class CounterStrikeEditor(Editor):
    """Editor to support editing Counter-Strike VODs into highlight videos and uploading them to YouTube."""

    @staticmethod
    def find_game_starting_point(game_vod: GameVod) -> int:
        initial_offset = 40
        max_attempts = 15

        vod_filepath = f"media/vods/{game_vod.match.create_unique_folder_path()}/{game_vod.filename}"
        video_capture = cv2.VideoCapture(vod_filepath)
        width = video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)

        # The video is 60 FPS. Jump two seconds forward each attempt.
        for i in range(60 * initial_offset, (60 * 40) + (max_attempts * 120), 120):
            current_offset = i / 60
            print(current_offset)

            # Extract a single frame from the game where the round timer is potentially visible.
            video_capture.set(cv2.CAP_PROP_POS_FRAMES, i)
            _res, frame = video_capture.read()

            # Crop the frame, so it focuses on the scoreboard and the timer.
            cropped_frame = frame[0:200, (int(width / 2) - 125):(int(width / 2) + 125)]
            cv2.imwrite(f"test/test-{i}.png", cropped_frame)

            # TODO: Use OCR to get the characters in the image and find the timer. If not found, try again with a new frame.

        # TODO: Convert the time on the timer to an offset for when the game starts compared to when the video starts.
        return 0
