import logging
import math

from PIL import Image, ImageDraw
from colorthief import ColorThief

from scrapers.models import Match, Team, Game
from videos.metadata.util import create_match_frame_part
from videos.models import VideoMetadata


def create_pre_match_video_metadata(scheduled_match: Match):
    """
    Create all metadata required for a YouTube video including a title, description, tags, and a thumbnail based on
    pre-match information.
    """
    logging.info(f"Creating pre-match video metadata for {scheduled_match}.")

    title = create_video_title(scheduled_match)
    description = create_video_description(scheduled_match)
    tags = create_video_tags(scheduled_match)

    thumbnail_filename = create_video_thumbnail(scheduled_match)

    VideoMetadata.objects.create(match=scheduled_match, title=title, description=description,
                                 tags=tags, thumbnail_filename=thumbnail_filename)


def create_video_title(scheduled_match: Match) -> str:
    """Use the teams, tournament, and, if necessary, extra match information to create a video title."""
    # TODO: Generate an eye catching initial part of the video title based on the context of the match.
    team_part = f"{scheduled_match.team_1.organization.name} vs {scheduled_match.team_2.organization.name}"
    basic_title = f"{team_part} - HIGHLIGHTS | {scheduled_match.tournament.name}"

    return basic_title


def create_video_description(scheduled_match: Match) -> str:
    """Use the teams, tournament, and, if necessary, extra match information to create a video description."""
    tournament = scheduled_match.tournament
    game = scheduled_match.team_1.get_game_display()

    match_part_prefix = "the game" if scheduled_match.format == Match.Format.BEST_OF_1 else "all maps"
    match_part = f"Highlights from {match_part_prefix} between {scheduled_match.team_1.organization.name} and " \
                 f"{scheduled_match.team_2.organization.name} ({scheduled_match.get_format_display()})\n" \
                 f"{scheduled_match.team_1.organization.name}: TEAM_1_PLAYERS\n" \
                 f"{scheduled_match.team_2.organization.name}: TEAM_2_PLAYERS\n"

    link_part = f"This is the TOURNAMENT_CONTEXT of the {tournament.prize_pool_us_dollars} prize pool " \
                f"{game} tournament {tournament.name}:\n" \
                f"Match: {scheduled_match.url}\n" \
                f"Tournament: {tournament.url}\n" \
                f"Credits: CREDIT_URL\n"

    channel_part = f"Highlightly brings you accurate highlights quickly, condensing all the best {game} has to offer. " \
                   f"Catch the best moments from all your favorite {game} teams. Watch the best players in the world " \
                   f"compete at the highest levels of {game}.\n"

    channels_part = "Highlightly channels:\n" \
                    "Counter-Strike: https://www.youtube.com/channel/UCaLgPz7aH58L4nDku2rYl1Q\n" \
                    "Valorant: https://www.youtube.com/channel/UCR40P8gajrDJcaP3Y5pQVxQ\n" \
                    "League of Legends: https://www.youtube.com/channel/UCH97dRgcN7vvhzpfAZRiUlg\n"

    game_name = game if game != "Counter-Strike" else "csgo"
    tags_part = f"#{scheduled_match.team_1.organization.name.replace(' ', '').lower()} " \
                f"#{scheduled_match.team_2.organization.name.replace(' ', '').lower()} " \
                f"#{game_name.replace(' ', '').replace('-', '').lower()}"

    return f"{match_part}\n{link_part}\n{channel_part}\n{channels_part}\n{tags_part}"


def create_video_tags(scheduled_match: Match) -> list[str]:
    """Use the teams, tournament, and, if necessary, extra match information to create tags for the video."""
    tags = [scheduled_match.team_1.organization.name, scheduled_match.team_2.organization.name,
            scheduled_match.tournament.name, scheduled_match.team_1.get_game_display(),
            scheduled_match.tournament.location, scheduled_match.team_1.nationality, scheduled_match.team_2.nationality,
            scheduled_match.get_format_display()]

    if scheduled_match.team_1.game == Game.COUNTER_STRIKE:
        tags.extend(["csgo", "global offensive", "blast", "paris major", "csgo major", "csgo paris major", "blast tv"])

    return tags


def create_video_thumbnail(scheduled_match: Match) -> str:
    """
    Use the team logos, tournament logo, tournament context, and if necessary, extra match information to create a
    thumbnail for the video. The name of the created thumbnail file is returned.
    """
    # To best fit a YouTube thumbnail, the image should be 1280 x 720.
    thumbnail = Image.new("RGB", (1280, 720), (255, 255, 255))

    # Add the "Game highlights" consistent text part to the left of the thumbnail.
    text_part = Image.open("media/thumbnail_text_part.png")
    thumbnail.paste(text_part, (0, 0))

    # For both teams, generate a thumbnail team logo if it does not already exist.
    team_1_part = create_team_logo_thumbnail_part(scheduled_match.team_1)
    team_2_part = create_team_logo_thumbnail_part(scheduled_match.team_2)

    # Put the thumbnail team logos in the left 1/4 of the thumbnail.
    thumbnail.paste(team_1_part, (text_part.width, 0))
    thumbnail.paste(team_2_part, (text_part.width, team_1_part.height))

    # Draw a border between the team logo parts.
    draw = ImageDraw.Draw(thumbnail)
    xy = (text_part.width, team_1_part.height - 1, text_part.width + team_1_part.width - 1, team_1_part.height - 1)
    draw.line(xy, fill=(255, 255, 255), width=3)

    # Add a temporary match frame for testing how the thumbnail looks before the actual match frame is added later.
    path = get_temporary_match_frame_path(scheduled_match.team_1.game)
    match_frame_part = create_match_frame_part(path, team_1_part.width + text_part.width, scheduled_match.team_1.game)
    thumbnail.paste(match_frame_part, (team_1_part.width + text_part.width, 0))

    # Save the thumbnail to a file and return the filename of the saved thumbnail.
    folder_path = scheduled_match.create_unique_folder_path()
    thumbnail_filename = "thumbnail.png"
    thumbnail.save(f"{folder_path}/{thumbnail_filename}")

    return thumbnail_filename


def create_team_logo_thumbnail_part(team: Team) -> Image.Image:
    """Create an image with a single background color and the logo of the team centered on the image."""
    logo_filepath = f"media/teams/{team.organization.logo_filename}"

    # To best fit a YouTube thumbnail, the background image should be 360 x 360
    background_color = get_logo_background_color(team, logo_filepath)
    background = Image.new("RGB", (360, 360), background_color)

    # Resize the logo, so it fits within the background image.
    new_width = 250
    logo = Image.open(logo_filepath).convert("RGBA")
    scale = (new_width / float(logo.size[0]))
    new_height = int((float(logo.size[1]) * float(scale)))
    logo = logo.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Put the logo on top of the background image.
    offset = ((360 - logo.width) // 2, (360 - logo.height) // 2)
    background.paste(logo, offset, logo)

    return background


def get_logo_background_color(team: Team, logo_filepath: str) -> str:
    """Generate a background color based on the dominant color in the logo."""
    if team.organization.background_color is None:
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
        team.organization.background_color = "#{0:02x}{1:02x}{2:02x}".format(clamp(r), clamp(g), clamp(b))
        team.organization.save()

    return team.organization.background_color


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


def get_temporary_match_frame_path(game: Game):
    """Return the file path to the temporary match frame for the given game."""
    if game == Game.COUNTER_STRIKE:
        return "media/match_frames/counter_strike_match_frame.png"
    elif game == Game.LEAGUE_OF_LEGENDS:
        return "media/match_frames/league_of_legends_match_frame.png"
    else:
        return "media/match_frames/valorant_match_frame.png"
