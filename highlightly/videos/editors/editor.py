import math
import shutil
import subprocess
from pathlib import Path

from pydub import AudioSegment
from pydub.silence import detect_silence

from scrapers.models import Match, GameVod
from videos.models import VideoMetadata


class Editor:
    @staticmethod
    def find_game_starting_point(game_vod: GameVod) -> int:
        """Return how many seconds there are in the given VOD before the game starts."""
        raise NotImplementedError

    # TODO: Look into efficient ways to add smoother transitions between clips.
    @staticmethod
    def create_highlight_video(game_vod: GameVod, target_filename: str, offset: int) -> None:
        """Use the highlights and the offset to edit the full VOD into a highlight video."""
        highlights = game_vod.highlight_set.all()

        folder_path = f"media/vods/{game_vod.match.create_unique_folder_path()}"
        vod_filepath = f"{folder_path}/{game_vod.filename}"
        Path(f"{folder_path}/clips").mkdir(parents=True, exist_ok=True)
        Path(f"{folder_path}/highlights").mkdir(parents=True, exist_ok=True)

        # For each highlight, cut the clip out and save the highlight clip to a temporary location.
        with open(f"{folder_path}/clips/clips.txt", "a") as clips_txt:
            for count, highlight in enumerate(highlights):
                # Add 5 seconds at the start and end and add more time to the end of the last highlight.
                duration = highlight.duration_seconds + (20 if count + 1 == len(highlights) else 10)
                start = (highlight.start_time_seconds + offset) - 5

                # Extend the clip 2 more seconds at the start and end to make it easier to find a silent point to cut on.
                start -= 2
                duration += 4

                cmd = f"ffmpeg -ss {start} -i {vod_filepath} -to {duration} -c copy " \
                      f"{folder_path}/clips/clip_{count + 1}.mkv"
                subprocess.run(cmd, shell=True)

                # Find a silent point in the first 4 seconds and last 4 seconds to cut on.
                # TODO: Further cut the video so it starts and ends in silence.

                clips_txt.write(f"file 'clip_{count + 1}.mkv'\n")

        # Combine the clips into a single highlight video file.
        cmd = f"ffmpeg -f concat -i {folder_path}/clips/clips.txt -codec copy {folder_path}/highlights/{target_filename}"
        subprocess.run(cmd, shell=True)

        shutil.rmtree(f"{folder_path}/clips")

    @staticmethod
    def combine_highlight_videos(target_filename: str, highlight_videos: list[str]) -> None:
        pass

    @staticmethod
    def upload_highlight_video(target_filename: str, video_metadata: VideoMetadata) -> None:
        pass

    def edit_and_upload_video(self, match: Match):
        """Using the highlights edit the full VODs into a highlight video and upload it to YouTube."""
        game_vod = match.gamevod_set.get(filename="game_2.mkv")
        offset = self.find_game_starting_point(game_vod)

        self.create_highlight_video(game_vod, game_vod.filename.replace('.mkv', '_highlights.mp4'), offset)

        # TODO: Combine the highlight video for each game VOD into a single full highlight video.
        # TODO: Upload the single combined video to YouTube using the created video metadata.


def get_optimal_cut_points(clip_filepath: str) -> (float, float):
    """
    Extract the speech from the video and find the optimal times to cut the video to avoid cutting in the middle of a word
    or sentence. The optimal times to cut within the first 4 seconds and last 4 seconds are returned.
    """
    audio = AudioSegment.from_file(clip_filepath)
    detected_silence = detect_silence(audio, min_silence_len=100, silence_thresh=-32)

    # Find the longest silence in the first 4 seconds and the last 4 seconds.
    start_limit = 4 * 1000
    end_limit = (round(audio.duration_seconds) - 4) * 1000

    start_silences = [silence for silence in detected_silence if silence[0] < start_limit]
    end_silences = [silence for silence in detected_silence if silence[1] > end_limit]

    start_time_seconds = 2
    duration_seconds = end_limit + 2

    # If there is a silence in the first 4 seconds find the time to cut to get the longest silence after starting.
    if len(start_silences) > 0:
        longest_start_silence = sorted(start_silences, key=lambda x: x[1] - x[0], reverse=True)[0]
        start_time_seconds = int(math.ceil(longest_start_silence[0] / 100.0)) * 100

    # If there is a silence in the last 4 seconds find the time to cut to get the longest silence before ending.
    if len(end_silences) > 0:
        longest_end_silence = sorted(end_silences, key=lambda x: x[1] - x[0], reverse=True)[0]
        duration_seconds = int(math.floor(longest_end_silence[1] / 100.0)) * 100

    return start_time_seconds / 1000, duration_seconds / 1000
