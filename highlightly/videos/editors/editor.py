from django.db.models import QuerySet

from highlights.models import Highlight
from scrapers.models import Match, GameVod
from videos.models import VideoMetadata


class Editor:
    @staticmethod
    def find_game_starting_point(game_vod: GameVod) -> int:
        """Return how many seconds there are in the given VOD before the game starts."""
        raise NotImplementedError

    @staticmethod
    def edit_highlight_video(filename: str, offset: int, highlights: QuerySet[Highlight]) -> None:
        pass

    @staticmethod
    def combine_highlight_videos(filename: str, highlight_videos: list[str]) -> None:
        pass

    @staticmethod
    def upload_highlight_video(filename: str, video_metadata: VideoMetadata) -> None:
        pass

    def edit_and_upload_video(self, match: Match):
        """Using the highlights edit the full VODs into a highlight video and upload it to YouTube."""
        for game_vod in match.gamevod_set.all():
            offset = self.find_game_starting_point(game_vod)
            highlights = game_vod.highlight_set.all()

            # TODO: Use the highlights and the offset to edit the full VOD into a highlight video.

        # TODO: Combine the highlight video for each game VOD into a single full highlight video.
        # TODO: Upload the single combined video to YouTube using the created video metadata.
