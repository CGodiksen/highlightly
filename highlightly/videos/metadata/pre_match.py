import math
from pathlib import Path

from PIL import Image, ImageDraw
from colorthief import ColorThief

from scrapers.models import Match, Team
from videos.models import VideoMetadata


def create_pre_match_video_metadata(scheduled_match: Match):
    """
    Create all metadata required for a YouTube video including a title, description, tags, and a thumbnail based on
    pre-match information.
    """
    title = create_video_title(scheduled_match)
    description = create_video_description(scheduled_match)
    tags = create_video_tags(scheduled_match)

    thumbnail_filename = create_video_thumbnail(scheduled_match)

    VideoMetadata.objects.create(match=scheduled_match, title=title, description=description,
                                 tags=tags, thumbnail_filename=thumbnail_filename)


def create_video_title(scheduled_match: Match) -> str:
    """Use the teams, tournament, and, if necessary, extra match information to create a video title."""
    # TODO: Generate an eye catching initial part of the video title based on the context of the match.
    team_part = f"{scheduled_match.team_1.name} vs {scheduled_match.team_2.name}"
    basic_title = f"{team_part} - HIGHLIGHTS | {scheduled_match.tournament.name}"

    return basic_title


def create_video_description(scheduled_match: Match) -> str:
    """Use the teams, tournament, and, if necessary, extra match information to create a video description."""
    tournament = scheduled_match.tournament
    game = scheduled_match.team_1.get_game_display()

    channel_part = f"Highlightly brings you accurate highlights quickly, condensing all the best {game} has to offer. " \
                   f"Catch the best moments from all your favorite {game} teams. Watch the best players in the world " \
                   f"compete at the highest levels of {game}.\n"

    match_part = f"Highlights from all maps between {scheduled_match.team_1.name} and {scheduled_match.team_2.name} " \
                 f"({scheduled_match.get_format_display()})\n" \
                 f"TOURNAMENT_CONTEXT of {tournament.prize_pool_us_dollars} prize pool " \
                 f"{game} tournament ({tournament.name})\n" \
                 f"Match: {scheduled_match.url}\n" \
                 f"Tournament: {tournament.url}\n"

    channels_part = "Highlightly channels:\n" \
                    "Counter-Strike: https://www.youtube.com/channel/UCaLgPz7aH58L4nDku2rYl1Q\n" \
                    "Valorant: https://www.youtube.com/channel/UCR40P8gajrDJcaP3Y5pQVxQ\n" \
                    "League of Legends: https://www.youtube.com/channel/UCH97dRgcN7vvhzpfAZRiUlg\n"

    tags_part = f"#{scheduled_match.team_1.name.replace(' ', '').lower()} " \
                f"#{scheduled_match.team_2.name.replace(' ', '').lower()} " \
                f"#{game.replace(' ', '').lower()}"

    return f"{channel_part}\n{match_part}\n{channels_part}\n{tags_part}"


def create_video_tags(scheduled_match: Match) -> list[str]:
    """Use the teams, tournament, and, if necessary, extra match information to create tags for the video."""
    return [scheduled_match.team_1.name, scheduled_match.team_2.name, scheduled_match.tournament.name,
            scheduled_match.team_1.get_game_display(), scheduled_match.tournament.location,
            scheduled_match.team_1.nationality, scheduled_match.team_2.nationality,
            scheduled_match.get_format_display()]


# TODO: Maybe add a consistent part in the left 1/10 of the thumbnail with a gradient that matches the game and says "'GAME' HIGHLIGHTS".
def create_video_thumbnail(scheduled_match: Match) -> str:
    """
    Use the team logos, tournament logo, tournament context, and if necessary, extra match information to create a
    thumbnail for the video. The name of the created thumbnail file is returned.
    """
    # To best fit a YouTube thumbnail, the image should be 1280 x 720.
    thumbnail = Image.new("RGB", (1280, 720), (255, 255, 255))

    # For both teams, generate a thumbnail team logo if it does not already exist.
    team_1_part = create_team_logo_thumbnail_part(scheduled_match.team_1)
    team_2_part = create_team_logo_thumbnail_part(scheduled_match.team_2)

    # Put the thumbnail team logos in the left 1/4 of the thumbnail.
    thumbnail.paste(team_1_part, (0, 0))
    thumbnail.paste(team_2_part, (0, team_1_part.height))

    # Draw a border between the team logo parts.
    draw = ImageDraw.Draw(thumbnail)
    draw.line((0, team_1_part.height - 1, team_1_part.width - 1, team_1_part.height - 1), fill=(255, 255, 255), width=3)

    # Add a temporary match frame for testing how the thumbnail looks before the actual match frame is added later.
    match_frame_part = create_match_frame_part("../data/test/match_frame.png", team_1_part.width)
    thumbnail.paste(match_frame_part, (team_1_part.width, 0))

    # Save the thumbnail to a file and return the filename of the saved thumbnail.
    folder_path = f"media/thumbnails/{scheduled_match.tournament.name.replace(' ', '_')}"
    Path(folder_path).mkdir(parents=True, exist_ok=True)

    thumbnail_filename = f"{scheduled_match.team_1.name}-{scheduled_match.team_2.name}.png".replace(' ', '_')
    thumbnail.save(f"{folder_path}/{thumbnail_filename}")

    return thumbnail_filename


def create_team_logo_thumbnail_part(team: Team) -> Image.Image:
    """Create an image with a single background color and the logo of the team centered on the image."""
    logo_filepath = f"media/teams/{team.logo_filename}"

    # To best fit a YouTube thumbnail, the background image should be 360 x 360
    background_color = get_logo_background_color(team, logo_filepath)
    background = Image.new("RGB", (360, 360), background_color)

    # Resize the logo, so it fits within the background image.
    logo = Image.open(logo_filepath)
    logo.thumbnail((250, 250))

    # Put the logo on top of the background image.
    offset = ((360 - logo.width) // 2, (360 - logo.height) // 2)
    background.paste(logo, offset, logo)

    return background


def get_logo_background_color(team: Team, logo_filepath: str) -> str:
    """Generate a background color based on the dominant color in the logo."""
    if team.background_color is None:
        color_thief = ColorThief(logo_filepath)
        dominant_color = color_thief.get_color(quality=1)
        palette = list(set(color_thief.get_palette()))

        # Handle the case where the logo is white since white is not a good background color.
        if get_color_distance(dominant_color, (255, 255, 255)) < 300:
            (r, g, b) = (0, 0, 0)
        # Handle the case where the logo is a single color without a border.
        elif is_single_colored(palette):
            (r, g, b) = (26, 44, 85)
        else:
            # Darken the color to make it a better background color.
            (r, g, b) = tuple(channel - 25 for channel in dominant_color)

        # Convert RGB to hex and save it on the team model to avoid calculating the background color each time.
        team.background_color = "#{0:02x}{1:02x}{2:02x}".format(clamp(r), clamp(g), clamp(b))
        team.save()

    return team.background_color


def create_match_frame_part(match_frame_filepath: str, team_part_width) -> Image.Image:
    """
    Given a filepath to a full size frame from a match, resize and crop the image to make it the correct size for the
    match frame part of the thumbnail.
    """
    match_frame = Image.open(match_frame_filepath)
    match_frame.thumbnail((1450, 820))

    cropped_width = match_frame.width - (1280 - team_part_width)
    cropped_height = match_frame.height - 720
    box = (cropped_width // 2, cropped_height, match_frame.width - (cropped_width // 2), match_frame.height)

    return match_frame.crop(box)


def is_single_colored(palette: list[tuple[int, int, int]]) -> bool:
    """Return True if the given palette can be interpreted as being of a single color."""
    max_color_distance = 0

    for current_color in palette:
        for color in palette:
            max_color_distance = max(max_color_distance, get_color_distance(current_color, color))

    return max_color_distance < 50


def get_color_distance(rgb_1: tuple[int, int, int], rgb_2: tuple[int, int, int]) -> float:
    """Return the "distance" between the two given colors."""
    red_mean = (rgb_1[0] + rgb_2[0]) / 2
    r = rgb_1[0] - rgb_2[0]
    g = rgb_1[1] - rgb_2[1]
    b = rgb_1[2] - rgb_2[2]

    return math.sqrt((int(((512 + red_mean) * r * r)) >> 8) + 4 * g * g + (int(((767 - red_mean) * b * b)) >> 8))


def clamp(x):
    return max(0, min(x, 255))
