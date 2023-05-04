import logging
import math
import shutil
import subprocess
from datetime import timedelta
from pathlib import Path

from pydub import AudioSegment
from pydub.silence import detect_silence

from highlights.models import Highlight
from scrapers.models import Match, GameVod
from videos.models import VideoMetadata


class Editor:
    @staticmethod
    def find_game_starting_point(game_vod: GameVod) -> int:
        """Return how many seconds there are in the given VOD before the game starts."""
        raise NotImplementedError

    @staticmethod
    def select_highlights(game_vod: GameVod) -> list[Highlight]:
        """Based on the wanted video length, select the best highlights from the possible highlights."""
        selected_highlights = []
        unsorted_highlights = game_vod.highlight_set.all()
        highlights = sorted(unsorted_highlights, key=lambda h: h.value / max(h.duration_seconds, 10), reverse=True)

        current_video_length_seconds = 0
        wanted_video_length_seconds = timedelta(minutes=game_vod.round_count * 0.45).total_seconds()

        logging.info(f"Selecting the best highlights for {wanted_video_length_seconds / 60} minute "
                     f"highlight video of {game_vod}.")

        # Pistol rounds (1, 16), the last round, and, if necessary, the last round of regulation should always be included.
        rounds_to_include = list({1, 16, game_vod.round_count})
        if game_vod.round_count > 30:
            rounds_to_include.append(30)

        for round in rounds_to_include:
            best_highlight = next((highlight for highlight in highlights if highlight.round_number == round), None)
            current_video_length_seconds += add_highlight_to_selected(selected_highlights, best_highlight, highlights)

        # Keep adding highlights until out of highlights or the wanted video length is reached.
        for highlight in highlights:
            if highlight not in selected_highlights:
                current_video_length_seconds += add_highlight_to_selected(selected_highlights, highlight, highlights)

            if current_video_length_seconds >= wanted_video_length_seconds:
                break

        logging.info(f"Selected {len(selected_highlights)} highlights for {current_video_length_seconds / 60} "
                     f"minute highlight video of {game_vod}.")

        return sorted(selected_highlights, key=lambda h: h.start_time_seconds)

    # TODO: Look into efficient ways to add smoother transitions between clips.
    @staticmethod
    def create_highlight_video(highlights: list[Highlight], game_vod: GameVod, target_filename: str, offset: int,
                               folder_path: str) -> None:
        """Use the highlights and the offset to edit the full VOD into a highlight video."""
        logging.info(f"Using {len(highlights)} highlights to cut {game_vod} into highlight video.")

        vod_filepath = f"{folder_path}/vods/{game_vod.filename}"
        Path(f"{folder_path}/clips").mkdir(parents=True, exist_ok=True)

        # For each highlight, cut the clip out and save the highlight clip to a temporary location.
        with open(f"{folder_path}/clips/clips.txt", "a+") as clips_txt:
            for count, highlight in enumerate(highlights):
                # Add 3 seconds at the start and 5 seconds at the end and add more time to the end of the last highlight.
                duration = highlight.duration_seconds + (15 if count + 1 == len(highlights) else 8)
                start = (highlight.start_time_seconds + offset) - 3

                # Create the initial full length clip.
                clip_temp_filepath = f"{folder_path}/clips/clip_{count + 1}_temp.mkv"
                cmd = f"ffmpeg -ss {start} -i {vod_filepath} -to {duration} -c copy {clip_temp_filepath}"
                subprocess.run(cmd, shell=True)

                # Find a silent point in the first 2 seconds and last 3 seconds to cut on.
                (silent_start, silent_end) = get_optimal_cut_points(clip_temp_filepath)

                # Further cut the video, so it starts and ends in silence.
                clip_filepath = clip_temp_filepath.replace("_temp.mkv", ".mkv")
                cmd = f"ffmpeg -ss {silent_start} -i {clip_temp_filepath} -to {silent_end - silent_start} -c copy {clip_filepath}"
                subprocess.run(cmd, shell=True)

                logging.info(f"Created {silent_end - silent_start} second highlight clip for round "
                             f"{highlight.round_number} of {game_vod}.")

                clips_txt.write(f"file 'clip_{count + 1}.mkv'\n")

        # Combine the clips into a single highlight video file.
        cmd = f"ffmpeg -f concat -i {folder_path}/clips/clips.txt -codec copy {folder_path}/highlights/{target_filename}"
        subprocess.run(cmd, shell=True)

        logging.info(f"Combined {len(highlights)} highlights into a single highlight video for {game_vod}.")

        shutil.rmtree(f"{folder_path}/clips")

    @staticmethod
    def upload_highlight_video(filepath: str, video_metadata: VideoMetadata) -> None:
        """Upload the single combined video to YouTube using the created video metadata."""
        # TODO: Set up OAuth authentication flow that uses the token and refresh token to avoid further login flows.
        # TODO: Set up use of the videos.insert endpoint. Look into if the video can be made public automatically or manually.
        # TODO: Request an audit of the client to make it possible to upload public videos in the future.
        # TODO: Maybe also look into if it will be necessary to request for more quota for uploading (currently only 6 videos a day).
        pass

    def edit_and_upload_video(self, match: Match):
        """Using the highlights edit the full VODs into a highlight video and upload it to YouTube."""
        folder_path = match.create_unique_folder_path()
        Path(f"{folder_path}/highlights").mkdir(parents=True, exist_ok=True)
        logging.info(f"Creating a highlight video for {match} at {folder_path}/highlights.")

        with open(f"{folder_path}/highlights/highlights.txt", "a+") as highlights_txt:
            for game_vod in match.gamevod_set.all():
                logging.info(f"Creating a highlight video for {game_vod}.")
                offset = self.find_game_starting_point(game_vod)

                highlights = self.select_highlights(game_vod)
                highlight_video_filename = game_vod.filename.replace('.mkv', '_highlights.mp4')
                self.create_highlight_video(highlights, game_vod, highlight_video_filename, offset, folder_path)

                highlights_txt.write(f"file '{highlight_video_filename}'\n")

        # Combine the highlight video for each game VOD into a single full highlight video.
        cmd = f"ffmpeg -f concat -i {folder_path}/highlights/highlights.txt -codec copy {folder_path}/highlights.mp4"
        subprocess.run(cmd, shell=True)

        logging.info(f"Combined {match.gamevod_set.count()} highlight videos into a single full "
                     f"highlight video for {match}.")

        shutil.rmtree(f"{folder_path}/highlights")

        self.upload_highlight_video(f"{folder_path}/highlights.mp4", match.videometadata)


# TODO: Maybe extend the time that is added to the start and end and extend the period we look for optimal cut points in.
# TODO: Maybe round up and down and add a millisecond for a slightly better cut point.
def get_optimal_cut_points(clip_filepath: str) -> (float, float):
    """
    Extract the speech from the video and find the optimal times to cut the video to avoid cutting in the middle of a word
    or sentence. The optimal times to cut within the first 2 seconds and last 3 seconds are returned.
    """
    audio = AudioSegment.from_file(clip_filepath)
    detected_silence = detect_silence(audio, min_silence_len=100, silence_thresh=-32)

    # Find the longest silence in the first 2 seconds and the last 3 seconds.
    start_limit_ms = 2 * 1000
    end_limit_ms = (round(audio.duration_seconds) - 3) * 1000

    start_silences = [silence for silence in detected_silence if silence[0] < start_limit_ms]
    end_silences = [silence for silence in detected_silence if silence[1] > end_limit_ms]

    start_time_ms = 1500
    end_time_ms = end_limit_ms + 1000

    # If there is a silence in the first 2 seconds find the time to cut to get the longest silence after starting.
    if len(start_silences) > 0:
        longest_start_silence = sorted(start_silences, key=lambda x: x[1] - x[0], reverse=True)[0]
        start_time_ms = int(math.ceil(longest_start_silence[0] / 100.0)) * 100

    # If there is a silence in the last 3 seconds find the time to cut to get the longest silence before ending.
    if len(end_silences) > 0:
        longest_end_silence = sorted(end_silences, key=lambda x: x[1] - x[0], reverse=True)[0]
        end_time_ms = int(math.floor(longest_end_silence[1] / 100.0)) * 100

    return start_time_ms / 1000, end_time_ms / 1000


def add_highlight_to_selected(selected_highlights: list[Highlight], highlight: Highlight | None,
                              highlights: list[Highlight]) -> int:
    """Add the given highlight to the selected highlights and return the number of seconds added."""
    added_duration = 0

    if highlight is not None:
        selected_highlights.append(highlight)
        added_duration += highlight.duration_seconds + 8  # Adding 8 seconds to account for the full clip length.

        round_highlights = [h for h in highlights if h.round_number == highlight.round_number]
        round_last_highlight = sorted(round_highlights, key=lambda h: h.start_time_seconds, reverse=True)[0]

        # If a highlight from a round is included, also include the last highlight to show how the round ends.
        if round_last_highlight not in selected_highlights:
            selected_highlights.append(round_last_highlight)
            added_duration += round_last_highlight.duration_seconds + 8  # Adding 8 seconds to account for the full clip length.

    return added_duration
