import logging
import os
import re

import cv2
import pandas as pd
import twitch
from PIL import Image
from html2image import Html2Image

from scrapers.models import Match, GameVod, Team
from videos.metadata.util import create_match_frame_part
from videos.models import VideoMetadata


def add_post_match_video_metadata(match: Match):
    """
    Add metadata to the video metadata that can only be extracted once the match is finished. This includes
    statistics about the performance of each player during the match, the tournament context, the tournament logo,
    and a frame from the match for the thumbnail.
    """
    logging.info(f"Creating post-match video metadata for {match}.")

    video_metadata = VideoMetadata.objects.get(match=match)
    new_tags = video_metadata.tags
    new_description = video_metadata.description

    # Extract the statistics for each time into a dataframe.
    statistics_folder_path = match.create_unique_folder_path("statistics")
    team_1_statistics = pd.read_csv(f"{statistics_folder_path}/{match.team_1_statistics_filename}")
    team_2_statistics = pd.read_csv(f"{statistics_folder_path}/{match.team_2_statistics_filename}")

    team_1_in_game_names = get_team_in_game_names(team_1_statistics)
    team_2_in_game_names = get_team_in_game_names(team_2_statistics)

    # Add the tournament context to the description and tags.
    new_description = new_description.replace("TOURNAMENT_CONTEXT", match.tournament_context)
    new_tags.append(match.tournament_context)

    # Add players to description and tags.
    new_description = new_description.replace("TEAM_1_PLAYERS", ", ".join(team_1_in_game_names))
    new_description = new_description.replace("TEAM_2_PLAYERS", ", ".join(team_2_in_game_names))
    new_tags.extend(team_1_in_game_names)
    new_tags.extend(team_2_in_game_names)

    # Add credit to where the VOD is from to the description.
    channel_name = get_match_vod_channel_name(match)
    new_description = new_description.replace("CREDIT_URL", f"https://www.twitch.tv/{channel_name.lower()}")

    # Add a frame from the match and the tournament logo to the thumbnail.
    finish_video_thumbnail(match, video_metadata)

    # TODO: Create an image with tables for the match statistics and the MVP of the match with player specific statistics.

    video_metadata.description = new_description
    video_metadata.tags = new_tags
    video_metadata.save()


def get_team_in_game_names(team_statistics: pd.DataFrame) -> list[str]:
    """Given a dataframe with the team statistics, extract the in-game names for all the players."""
    player_names: pd.Series = team_statistics.iloc[:, 0]
    extract_in_game_name = lambda match: re.search("'(.*?)'", match.group()).group().strip("'")
    in_game_names: pd.Series = player_names.str.replace("[\s\S]+", extract_in_game_name, regex=True)

    return in_game_names.tolist()


def get_match_vod_channel_name(match: Match) -> str:
    """Return the channel name of the Twitch channel that streamed the match."""
    split_url = match.gamevod_set.all().first().url.split("&")
    video_id = split_url[0].removeprefix("https://player.twitch.tv/?video=v")

    helix = twitch.Helix(os.environ["TWITCH_CLIENT_ID"], os.environ["TWITCH_CLIENT_SECRET"])
    return helix.video(int(video_id)).user_name


# TODO: Generate some eye catching text based on the context of the match and put it in the top of the match frame.
def finish_video_thumbnail(match: Match, video_metadata: VideoMetadata) -> None:
    """Replace the previous video thumbnail with a new file that has a match frame and the tournament logo added."""
    thumbnail_folder = match.create_unique_folder_path()
    thumbnail = Image.open(f"{thumbnail_folder}/{video_metadata.thumbnail_filename}")

    # Retrieve a frame from one minute into the first game in the match.
    vod_filepath = f"{match.create_unique_folder_path('vods')}/{match.gamevod_set.first().filename}"
    video_capture = cv2.VideoCapture(vod_filepath)
    video_capture.set(cv2.CAP_PROP_POS_FRAMES, 60 * 60)

    _res, frame = video_capture.read()
    frame_filepath = f"{thumbnail_folder}/{video_metadata.thumbnail_filename.replace('.png', '_frame.png')}"
    cv2.imwrite(frame_filepath, frame)

    # Add the frame from the match to the right 3/5 of the thumbnail.
    match_frame_part = create_match_frame_part(frame_filepath, 360 + 160)
    thumbnail.paste(match_frame_part, (360 + 160, 0))
    os.remove(frame_filepath)

    # Add the tournament logo in the bottom right of the thumbnail.
    tournament_logo = Image.open(f"media/tournaments/{match.tournament.logo_filename}")
    tournament_logo.resize((150, 150))
    thumbnail.paste(tournament_logo, (1250 - tournament_logo.width, 30), tournament_logo)

    thumbnail.save(f"{thumbnail_folder}/{video_metadata.thumbnail_filename}")
    logging.info(f"Added match frame and tournament logo to thumbnail at {video_metadata.thumbnail_filename}.")


# TODO: Retrieve the per team round count instead of the total round count.
# TODO: Retrieve the player photo of the best player of each map and the entire match (persist this in a player object).
# TODO: Add flags to team names in table.
def create_game_statistics(match: Match):
    """Create an image that contains the statistics for each game and for the total match statistics."""
    game: GameVod = match.gamevod_set.first()

    # Pass the data of the game into the html file.
    with open("videos/html/post-match-statistics.html") as html_file:
        team_1_data = get_team_statistics_data(game, match.team_1, 1)
        team_2_data = get_team_statistics_data(game, match.team_2, 2)

        general_data = {"match_info": f"Map {game.game_count} - {game.map}", "mvp_title": f"Map {game.game_count} MVP",
                        "mvp_profile_picture": os.path.abspath(f"media/players/9z_buda.png"),
                        "mvp_name": "Nicolás &nbsp;'<b>buda</b>'&nbsp; Kramer"}

        html = html_file.read().format(**team_1_data, **team_2_data, **general_data)

        hti = Html2Image()
        hti.screenshot(html_str=html, css_file="videos/html/post-match-statistics.css", save_as="out.png")


def get_team_statistics_data(game: GameVod, team: Team, team_number: int) -> dict:
    """Return a dict that can be used to populate the HTML for the post match statistics image."""
    team_logo_filepath = os.path.abspath(f"media/teams/{team.logo_filename}")

    team_data = {f"team_{team_number}_name": team.name, f"team_{team_number}_score": 14,
                 f"team_{team_number}_result": "loser", f"team_{team_number}_logo": team_logo_filepath}

    statistics_filename = game.team_1_statistics_filename if team_number == 1 else game.team_2_statistics_filename
    df = pd.read_csv(f"{game.match.create_unique_folder_path('statistics')}/{statistics_filename}")

    columns = ["name", "kd", "plus_minus", "adr", "kast", "rating"]
    for column_count, column in enumerate(columns):
        for value_count, value in enumerate(df.iloc[:,column_count].tolist()):
            team_data[f"team_{team_number}_player_{value_count + 1}_{column}"] = value

            if column == "plus_minus":
                sign = "plus" if value > 0 else "minus" if value < 0 else ""
                team_data[f"team_{team_number}_player_{value_count + 1}_sign"] = sign

    return team_data
