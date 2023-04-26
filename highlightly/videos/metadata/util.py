from PIL import Image


def create_match_frame_part(match_frame_filepath: str, team_part_width: int) -> Image.Image:
    """
    Given a filepath to a full size frame from a match, resize and crop the image to make it the correct size for the
    match frame part of the thumbnail.
    """
    match_frame = Image.open(match_frame_filepath).resize((1920, 1080))
    match_frame.thumbnail((1450, 820))

    cropped_width = match_frame.width - (1280 - team_part_width)
    cropped_height = match_frame.height - 720
    box = (cropped_width // 2, cropped_height, match_frame.width - (cropped_width // 2), match_frame.height)

    return match_frame.crop(box)
