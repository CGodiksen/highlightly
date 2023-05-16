from PIL import Image

from scrapers.models import Game


# TODO: For league of legends find a better temporary match frame that is more realistic.
# TODO: For League of Legends and valorant, zoom into the image center way more.
def create_match_frame_part(match_frame_filepath: str, team_part_width: int, game: Game) -> Image.Image:
    """
    Given a filepath to a full size frame from a match, resize and crop the image to make it the correct size for the
    match frame part of the thumbnail.
    """
    match_frame = Image.open(match_frame_filepath).resize((1920, 1080))
    match_frame.thumbnail(get_game_match_frame_size(game))

    cropped_width = match_frame.width - (1280 - team_part_width)
    cropped_height = match_frame.height - 720
    box = (cropped_width // 2, cropped_height, match_frame.width - (cropped_width // 2), match_frame.height)

    return match_frame.crop(box)


def get_game_match_frame_size(game: Game) -> tuple[int, int]:
    """Return the resized size of the match frame based on the game."""
    if game == Game.COUNTER_STRIKE:
        return 1450, 820
    else:
        return 1650, 1020
