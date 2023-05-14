import logging
import math
import shutil
import subprocess
from datetime import timedelta
from pathlib import Path

from highlights.models import Highlight
from scrapers.models import Match, GameVod
from videos.metadata.post_match import create_game_statistics_image
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
        round_count = game_vod.team_1_round_count + game_vod.team_2_round_count
        wanted_video_length_seconds = timedelta(minutes=round_count * 0.45).total_seconds()

        logging.info(f"Selecting the best highlights for {wanted_video_length_seconds / 60} minute "
                     f"highlight video of {game_vod}.")

        # Pistol rounds (1, 16), the last round, and, if necessary, the last round of regulation should always be included.
        rounds_to_include = list({1, 16, round_count})
        if round_count > 30:
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

    @staticmethod
    def create_highlight_video(highlights: list[Highlight], game_vod: GameVod, target_filename: str, offset: int,
                               folder_path: str) -> None:
        """Use the highlights and the offset to edit the full VOD into a highlight video."""
        logging.info(f"Using {len(highlights)} highlights to cut {game_vod} into highlight video.")

        vod_filepath = f"{folder_path}/vods/{game_vod.filename}"
        Path(f"{folder_path}/clips").mkdir(parents=True, exist_ok=True)

        # For each highlight, cut the clip out and save the highlight clip to a temporary location.
        exact_durations = []
        for count, highlight in enumerate(highlights):
            is_last = count + 1 == len(highlights)

            # Add 3 seconds at the start and 4 seconds at the end and add more time to the end of the last highlight.
            duration = highlight.duration_seconds + (19 if is_last else 7)
            start = (highlight.start_time_seconds + offset) - 3

            clip_filepath = f"{folder_path}/clips/temp_clip_{count + 1}.mkv" if is_last else f"{folder_path}/clips/clip_{count + 1}.mkv"
            cmd = f"ffmpeg -ss {start} -i {vod_filepath} -to {duration} -c copy {clip_filepath}"
            subprocess.run(cmd, shell=True)

            exact_duration = get_video_length(clip_filepath)

            # If it is the last highlight, replace the last 10 seconds of the video with the post game statistics.
            if is_last:
                create_game_statistics_image(game_vod, folder_path, f"game_{game_vod.game_count}.png")

                # Create a 10-second video with the post game statistics image using the same frame rate as the clip.
                frame_rate = get_video_frame_rate(clip_filepath)
                statistics_filepath = f"{folder_path}/clips/statistics.mkv"
                cmd = f"ffmpeg -loop 1 -i {folder_path}/game_{game_vod.game_count}.png -filter:v fps={frame_rate} -t 10 {statistics_filepath}"
                subprocess.run(cmd, shell=True)

                # Combine the statistics video and the clip into the complete final highlight clip.
                cmd = f"ffmpeg -i {clip_filepath} -i {statistics_filepath} -filter_complex " \
                      f"'xfade=transition=fade:offset={exact_duration - 11}:duration=1' -c:a copy {clip_filepath.replace('temp_', '')}"
                subprocess.run(cmd, shell=True)

            logging.info(f"Created {duration} second highlight clip for round {highlight.round_number} of {game_vod}.")
            exact_durations.append(exact_duration)

        combine_clips_with_crossfade(folder_path, target_filename, exact_durations)
        logging.info(f"Combined {len(highlights)} highlights into a single highlight video for {game_vod}.")

        # TODO: Call function to create post match statistics.
        # TODO: Add 15 seconds extra to last highlight. 5 seconds for the actual video and 10 seconds for the statistics.
        # TODO: Replace the last 10 seconds of video with the post match statistics and keep the audio as it were.

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
                highlight_video_filename = game_vod.filename.replace(".mkv", "_highlights.mp4")
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
        added_duration += highlight.duration_seconds + 7  # Adding 7 seconds to account for the full clip length.

        round_highlights = [h for h in highlights if h.round_number == highlight.round_number]
        round_last_highlight = sorted(round_highlights, key=lambda h: h.start_time_seconds, reverse=True)[0]

        # If a highlight from a round is included, also include the last highlight to show how the round ends.
        if highlight.id != round_last_highlight.id and round_last_highlight not in selected_highlights:
            selected_highlights.append(round_last_highlight)
            added_duration += round_last_highlight.duration_seconds + 7  # Adding 7 seconds to account for the full clip length.

    return added_duration


# TODO: Find a way to combine all the clips in a single command without running out of memory.
def combine_clips_with_crossfade(folder_path: str, target_filename: str, clip_durations: list[float]):
    """Combine the given clips, adding a crossfade effect between each clip for cleaner transitions."""
    # Split the clips into groups of 10 to avoid memory issues with combining them all with a single command.
    group_size = 10
    groups = math.ceil(len(clip_durations) / group_size)

    if len(clip_durations) % 10 == 1:
        group_size = 9

    Path(f"{folder_path}/highlights/groups").mkdir(parents=True, exist_ok=True)

    with open(f"{folder_path}/highlights/groups/groups.txt", "a+") as groups_txt:
        for group in range(groups):
            group_video_filters = []
            group_audio_filters = []
            group_file_ids = list(range(group * group_size, min((group * group_size) + group_size, len(clip_durations))))

            fade_offset = 0
            for i in range(len(group_file_ids) - 1):
                fade_offset += clip_durations[i + group * group_size] - 1

                v_filter_start = "[0]" if i == 0 else f"[vfade{i}]"
                v_filter_end = ",format=yuv420p" if i + 1 == len(group_file_ids) - 1 else f"[vfade{i + 1}]"
                group_video_filters.append(f"{v_filter_start}[{i + 1}:v]xfade=transition=fade:duration=1"
                                           f":offset={fade_offset}{v_filter_end}")

                a_filter_start = "[0:a]" if i == 0 else f"[afade{i}]"
                a_filter_end = "" if i + 1 == len(group_file_ids) - 1 else f"[afade{i + 1}]"
                group_audio_filters.append(f"{a_filter_start}[{i + 1}:a]acrossfade=d=1{a_filter_end}")

            # Combine the clips in the group into a single highlight video file.
            clips_part = " ".join([f'-i {folder_path}/clips/clip_{i + 1}.mkv' for i in group_file_ids])
            group_video_filename = target_filename.replace('.mp4', f'_{group}.mp4')
            cmd = f"ffmpeg {clips_part} -filter_complex 'afade=t=in:ss=0:d=1[0:a], {'; '.join(group_video_filters)}; " \
                  f"{'; '.join(group_audio_filters)}, afade=t=out:st={fade_offset + clip_durations[group_file_ids[-1]] - 2}:d=2' " \
                  f"-preset superfast -crf 27 -movflags +faststart {folder_path}/highlights/groups/{group_video_filename}"

            subprocess.run(cmd, shell=True)

            groups_txt.write(f"file '{group_video_filename}'\n")

    # Combine each group highlight video into a single file for the entire game.
    cmd = f"ffmpeg -f concat -i {folder_path}/highlights/groups/groups.txt -codec copy {folder_path}/highlights/{target_filename}"
    subprocess.run(cmd, shell=True)

    shutil.rmtree(f"{folder_path}/highlights/groups")


def get_video_length(filepath: str) -> float:
    """Use ffprope to get the video length in seconds."""
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {filepath}"
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

    return float(result.stdout)


def get_video_frame_rate(filepath: str) -> float:
    """Use ffprope to get the video frame rate in frames per second."""
    cmd = f"ffprobe -v 0 -of csv=p=0 -select_streams v:0 -show_entries stream=r_frame_rate {filepath}"
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

    return eval(result.stdout.strip())
