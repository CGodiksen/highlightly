import subprocess
from pathlib import Path

from scrapers.models import Match, GameVod
from videos.models import VideoMetadata


class Editor:
    @staticmethod
    def find_game_starting_point(game_vod: GameVod) -> int:
        """Return how many seconds there are in the given VOD before the game starts."""
        raise NotImplementedError

    # TODO: Look into methods for avoiding cutting in the middle of a word or sentence.
    # TODO: Maybe look through audio for whole video and determine ideal places to cut.
    # TODO: Then if the end time for a highlight is close to the ideal point, change the end time.
    # TODO: Add more time at the end of the last highlight.
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
                start = highlight.start_time_seconds + offset
                cmd = f"ffmpeg -ss {start} -i {vod_filepath} -to {highlight.duration_seconds} -c copy " \
                      f"{folder_path}/clips/clip_{count + 1}.mkv"
                subprocess.run(cmd, shell=True)

                clips_txt.write(f"file 'clip_{count + 1}.mkv'\n")

        # Combine the clips into a single highlight video file.
        cmd = f"ffmpeg -f concat -i {folder_path}/clips/clips.txt -codec copy {folder_path}/highlights/{target_filename}"
        subprocess.run(cmd, shell=True)

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

        self.create_highlight_video(game_vod, game_vod.filename.replace('.mkv', '_highlights.mkv'), offset)

        # TODO: Combine the highlight video for each game VOD into a single full highlight video.
        # TODO: Upload the single combined video to YouTube using the created video metadata.
