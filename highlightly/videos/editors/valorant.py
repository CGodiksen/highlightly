from scrapers.models import GameVod
from videos.editors.editor import Editor


class ValorantEditor(Editor):
    """Editor to support editing Valorant VODs into highlight videos and uploading them to YouTube."""

    def __init__(self) -> None:
        super().__init__()
        self.second_pistol_round = 13
        self.final_round = 24
        self.extra_start_time = 3
        self.extra_duration = 7

    @staticmethod
    def find_game_starting_point(game_vod: GameVod) -> int:
        """Return 0 since the highlight times are extracted directly from the VOD."""
        return 0
