from highlights.models import Highlight
from scrapers.models import GameVod
from videos.editors.editor import Editor


class LeagueOfLegendsEditor(Editor):
    """Editor to support editing League of Legends VODs into highlight videos and uploading them to YouTube."""

    def __init__(self) -> None:
        super().__init__()
        self.extra_start_time = 8
        self.extra_duration = 13

    @staticmethod
    def find_game_starting_point(game_vod: GameVod) -> int:
        """Return 0 since the highlight times are extracted directly from the VOD."""
        return 0

    def select_highlights(self, game_vod: GameVod) -> list[Highlight]:
        """Include all highlights from the game."""
        return list(game_vod.highlight_set.all().order_by("start_time_seconds"))
