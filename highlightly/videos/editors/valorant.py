from scrapers.models import GameVod
from videos.editors.editor import Editor


class ValorantEditor(Editor):
    """Editor to support editing Valorant VODs into highlight videos and uploading them to YouTube."""

    @staticmethod
    def find_game_starting_point(game_vod: GameVod) -> int:
        pass
