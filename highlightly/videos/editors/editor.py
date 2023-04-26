from scrapers.models import Match, GameVod


class Editor:
    @staticmethod
    def find_game_starting_point(game_vod: GameVod) -> int:
        """Return how many seconds there are in the given VOD before the game starts."""
        raise NotImplementedError

    def edit_and_upload_video(self, match: Match):
        """Using the highlights edit the full VODs into a highlight video and upload it to YouTube."""
        pass
