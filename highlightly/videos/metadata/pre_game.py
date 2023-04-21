import json
import math

from PIL import Image, ImageDraw
from colorthief import ColorThief

from scrapers.models import ScheduledMatch, Team
from videos.models import VideoMetadata


def create_pre_match_video_metadata(scheduled_match: ScheduledMatch):
    """
    Create all metadata required for a YouTube video including a title, description, tags, and a thumbnail based on
    pre-match information.
    """
    title = create_video_title(scheduled_match)
    description = create_video_description(scheduled_match)
    tags = create_video_tags(scheduled_match)

    thumbnail_filename = create_video_thumbnail(scheduled_match)

    VideoMetadata.objects.create(title=title, description=description, tags=json.dumps(tags),
                                 thumbnail_filename=thumbnail_filename)


def create_video_title(scheduled_match: ScheduledMatch) -> str:
    """Use the teams, tournament, and, if necessary, extra match information to create a video title."""
    # TODO: Generate an eye catching initial part of the video title based on the context of the match.
    team_part = f"{scheduled_match.team_1.name} vs {scheduled_match.team_2.name}"
    basic_title = f"{team_part} - HIGHLIGHTS | {scheduled_match.tournament.name}"

    return basic_title


# TODO: Maybe add the players from each team to the description when doing post game metadata.
# TODO: Maybe add the credits for where the vod is from.
def create_video_description(scheduled_match: ScheduledMatch) -> str:
    """Use the teams, tournament, and, if necessary, extra match information to create a video description."""
    tournament = scheduled_match.tournament
    game = scheduled_match.team_1.get_game_display()

    channel_part = f"Highlightly brings you accurate highlights quickly, condensing all the best {game} has to offer. " \
                   f"Catch the best moments from all your favorite {game} teams. Watch the best players in the world" \
                   f"compete at the highest levels of {game}.\n"

    match_part = f"Highlights from all maps between {scheduled_match.team_1.name} and {scheduled_match.team_2.name} " \
                 f"({scheduled_match.get_format_display()})\n" \
                 f"{scheduled_match.tournament_context.title()} of {tournament.prize_pool_us_dollars} prize pool " \
                 f"{game} tournament ({tournament.name})\n" \
                 f"Match: {scheduled_match.url}\n" \
                 f"Tournament: {tournament.url}\n"

    channels_part = "Highlightly channels:\n" \
                    "Counter-Strike: https://www.youtube.com/channel/UCaLgPz7aH58L4nDku2rYl1Q\n" \
                    "Valorant: https://www.youtube.com/channel/UCR40P8gajrDJcaP3Y5pQVxQ\n" \
                    "League of Legends: https://www.youtube.com/channel/UCH97dRgcN7vvhzpfAZRiUlg\n"

    tags_part = f"#{scheduled_match.team_1.name.lower()} #{scheduled_match.team_2.name.lower()} #{game.replace(' ', '').lower()}"

    return f"{channel_part}\n{match_part}\n{channels_part}\n{tags_part}"


# TODO: Maybe add the players from each team when doing post game metadata.
def create_video_tags(scheduled_match: ScheduledMatch) -> list[str]:
    """Use the teams, tournament, and, if necessary, extra match information to create tags for the video."""
    return [scheduled_match.team_1.name, scheduled_match.team_2.name, scheduled_match.tournament.name,
            scheduled_match.team_1.get_game_display(), scheduled_match.tournament.location,
            scheduled_match.team_1.nationality, scheduled_match.team_2.nationality, scheduled_match.tournament_context,
            scheduled_match.get_format_display()]


# TODO: When doing post game metadata, get a frame of the vod from right before a kill and use it for the game part.
def create_video_thumbnail(scheduled_match: ScheduledMatch) -> str:
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
    draw.line((0, team_1_part.height, team_1_part.width - 1, team_1_part.height), fill=(255, 255, 255), width=3)

    # Put the tournament logo in the bottom right of the thumbnail.
    tournament_logo = Image.open(f"media/tournaments/{scheduled_match.tournament.logo_filename}")
    tournament_logo.thumbnail((250, 250))
    thumbnail.paste(tournament_logo, (1250 - tournament_logo.width, 690 - tournament_logo.height), tournament_logo)

    thumbnail.save("thumbnail-test.png")
    # TODO: Maybe add a consistent part in the left 1/10 of the thumbnail with a gradient that matches the game and
    #  says "'GAME' HIGHLIGHTS".

    return ""


def create_team_logo_thumbnail_part(team: Team) -> Image.Image:
    """Generate a background color based on the dominant color in the logo and center the logo in a square image."""
    logo_filepath = f"media/teams/{team.logo_filename}"
    color_thief = ColorThief(logo_filepath)
    dominant_color = color_thief.get_color(quality=1)

    # TODO: Handle the case where the logo is a single color without a border.
    # TODO: Handle the case where the logo is white since white is not a good background color.
    # TODO: Maybe only darken the background color.
    # Lighting or darken the color to make it a better background color.
    color_change = -25 if is_light(dominant_color) else 25
    background_color = tuple(channel + color_change for channel in dominant_color)

    # To best fit a YouTube thumbnail, the background image should be 360 x 360
    background = Image.new("RGB", (360, 360), background_color)

    # Resize the logo, so it fits within the background image.
    logo = Image.open(logo_filepath)
    logo.thumbnail((250, 250))

    # Put the logo on top of the background image.
    offset = ((360 - logo.width) // 2, (360 - logo.height) // 2)
    background.paste(logo, offset, logo)

    return background


def is_light(rgb):
    """Return True if the given RGB color is light according to the HSP equation."""
    [r, g, b] = rgb

    hsp = math.sqrt(0.299 * (r * r) + 0.587 * (g * g) + 0.114 * (b * b))
    return hsp > 127.5
