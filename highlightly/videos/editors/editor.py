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
        # TODO: Maybe weigh longer clips higher to avoid many smalls cuts.
        # TODO: Maybe scale the highlight when setting the value based on how far away the length is from an ideal length.
        highlights = sorted(unsorted_highlights, key=lambda h: h.value / max(h.duration_seconds, 30), reverse=True)

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

        # TODO: Add crossfade transitions between each clip.
        # TODO: For each pair of clips, find the exact keyframe to cut on at the end of the first and start of the second.
        # TODO: Cut out the fade clips and add crossfade between the two cut out fade clips.
        # TODO: Add the single crossfade clip between the two original clips.

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


def add_highlight_to_selected(selected_highlights: list[Highlight], highlight: Highlight | None,
                              highlights: list[Highlight]) -> int:
    """Add the given highlight to the selected highlights and return the number of seconds added."""
    added_duration = 0

    if highlight is not None and highlight not in selected_highlights:
        selected_highlights.append(highlight)
        added_duration += highlight.duration_seconds + 8  # Adding 8 seconds to account for the full clip length.

        round_highlights = [h for h in highlights if h.round_number == highlight.round_number]
        round_last_highlight = sorted(round_highlights, key=lambda h: h.start_time_seconds, reverse=True)[0]

        # If a highlight from a round is included, also include the last highlight to show how the round ends.
        if highlight.id != round_last_highlight.id and round_last_highlight not in selected_highlights:
            selected_highlights.append(round_last_highlight)
            added_duration += round_last_highlight.duration_seconds + 8  # Adding 8 seconds to account for the full clip length.

    return added_duration
