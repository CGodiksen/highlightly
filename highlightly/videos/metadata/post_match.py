import logging
import os
import random
import re

import cv2
import pandas as pd
import twitch
from PIL import Image
from html2image import Html2Image

from scrapers.models import Match, GameVod, Team, Game
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
    game_1: GameVod = match.gamevod_set.first()
    team_1_statistics = pd.read_csv(f"{statistics_folder_path}/{game_1.team_1_statistics_filename}")
    team_2_statistics = pd.read_csv(f"{statistics_folder_path}/{game_1.team_2_statistics_filename}")

    team_1_in_game_names = get_team_in_game_names(team_1_statistics, match.team_1.game)
    team_2_in_game_names = get_team_in_game_names(team_2_statistics, match.team_2.game)

    # Add the tournament context to the description and tags.
    new_description = new_description.replace("TOURNAMENT_CONTEXT", match.tournament_context)
    new_tags.append(match.tournament_context)

    # Add players to description and tags.
    new_description = new_description.replace("TEAM_1_PLAYERS", ", ".join(team_1_in_game_names))
    new_description = new_description.replace("TEAM_2_PLAYERS", ", ".join(team_2_in_game_names))
    new_tags.extend(team_1_in_game_names)
    new_tags.extend(team_2_in_game_names)

    # Add credit to where the VOD is from to the description.
    short_name = match.tournament.short_name
    channel_name = get_match_vod_channel_name(match) if game_1.host == GameVod.Host.TWITCH else short_name
    new_description = new_description.replace("CREDIT_URL", f"https://www.twitch.tv/{channel_name.lower()}")

    # Add a frame from the match and the tournament logo to the thumbnail.
    finish_video_thumbnail(match, video_metadata, None)

    video_metadata.description = new_description
    video_metadata.tags = new_tags
    video_metadata.save()


def get_team_in_game_names(team_statistics: pd.DataFrame, game: Game) -> list[str]:
    """Given a dataframe with the team statistics, extract the in-game names for all the players."""
    player_names: pd.Series = team_statistics.iloc[:, 1 if game == Game.LEAGUE_OF_LEGENDS else 0]

    if game == Game.COUNTER_STRIKE or game == Game.LEAGUE_OF_LEGENDS:
        extract_in_game_name = lambda match: re.search("'(.*?)'", match.group()).group().strip("'")
        in_game_names: pd.Series = player_names.str.replace("[\s\S]+", extract_in_game_name, regex=True)
    else:
        in_game_names = player_names

    return in_game_names.tolist()


def get_match_vod_channel_name(match: Match) -> str:
    """Return the channel name of the Twitch channel that streamed the match."""
    split_url = match.gamevod_set.all().first().url.split("&")
    video_id = split_url[0].removeprefix("https://player.twitch.tv/?video=v")
    video_id = video_id.removeprefix("https://www.twitch.tv/videos/")

    helix = twitch.Helix(os.environ["TWITCH_CLIENT_ID"], os.environ["TWITCH_CLIENT_SECRET"])
    return helix.video(int(video_id)).user_name


# TODO: Generate some eye catching text based on the context of the match and put it in the top of the match frame.
def finish_video_thumbnail(match: Match, video_metadata: VideoMetadata, match_frame_time: float | None) -> None:
    """Replace the previous video thumbnail with a new file that has a match frame and the tournament logo added."""
    thumbnail_folder = match.create_unique_folder_path()
    thumbnail = Image.open(f"{thumbnail_folder}/{video_metadata.thumbnail_filename}")

    # Retrieve a frame right before a kill in the first game in the match.
    frame_filepath = f"{thumbnail_folder}/{video_metadata.thumbnail_filename.replace('.png', '_frame.png')}"
    match_frame_time: float = save_match_frame(match, frame_filepath, match_frame_time)
    video_metadata.thumbnail_match_frame_time = match_frame_time
    video_metadata.save()

    # Add the frame from the match to the right 3/5 of the thumbnail.
    match_frame_part = create_match_frame_part(frame_filepath, 360 + 160, match.team_1.game)
    thumbnail.paste(match_frame_part, (360 + 160, 0))
    os.remove(frame_filepath)

    # Add the tournament logo in the top right of the thumbnail.
    tournament_logo = Image.open(f"media/tournaments/{match.tournament.logo_filename}").convert("RGBA")
    tournament_logo = tournament_logo.resize((150, 150))
    thumbnail.paste(tournament_logo, (1250 - tournament_logo.width, 30), tournament_logo)

    thumbnail.save(f"{thumbnail_folder}/{video_metadata.thumbnail_filename}")
    logging.info(f"Added match frame and tournament logo to thumbnail at {video_metadata.thumbnail_filename}.")


def save_match_frame(match: Match, frame_filepath: str, frame_time: float | None) -> float:
    """Retrieve a frame right before a kill in the first game in the match and save it to the given filepath."""
    # Select a random highlight from the highlights.
    if frame_time is None:
        first_game: GameVod = match.gamevod_set.first()
        highlight = random.choice(first_game.highlight_set.all())
        highlight_second = highlight.start_time_seconds + first_game.game_start_offset
        frame_time = highlight_second + random.randint(0, highlight.duration_seconds)

    # Extract the frame from the VOD and save it.
    vod_filepath = f"{match.create_unique_folder_path('vods')}/{match.gamevod_set.first().filename}"
    video_capture = cv2.VideoCapture(vod_filepath)
    video_capture.set(cv2.CAP_PROP_POS_FRAMES, 60 * frame_time)

    _res, frame = video_capture.read()
    cv2.imwrite(frame_filepath, frame)

    return frame_time


# TODO: Add flags to team names in table.
# TODO: Replace the final map statistics with total match statistics.
def create_game_statistics_image(game: GameVod, folder_path: str, filename: str) -> None:
    """Create an image that contains the statistics for each game and for the total match statistics."""
    game_name = game.match.team_1.game.lower().replace("_", "-").replace(" ", "-")

    # Pass the data of the game into the html file.
    with open(f"videos/html/post-match-statistics-{game_name}.html") as html_file:
        team_1_data = get_team_statistics_data(game, game.match.team_1, 1, game_name)
        team_2_data = get_team_statistics_data(game, game.match.team_2, 2, game_name)

        match_info = game.map if game.match.format == Match.Format.BEST_OF_1 else f"Map {game.game_count} - {game.map}"
        match_info = f"Game {game.game_count}" if game_name == "league-of-legends" else match_info

        mvp_title_prefix = "Game" if game_name == "league-of-legends" else "Map"
        mvp_title = "Match MVP" if game.match.format == Match.Format.BEST_OF_1 else f"{mvp_title_prefix} {game.game_count} MVP"

        mvp_profile_picture = os.path.abspath(f"media/players/{game.mvp.profile_picture_filename}")

        general_data = {"match_info": match_info, "mvp_title": mvp_title,
                        "mvp_profile_picture": mvp_profile_picture, "mvp_name": str(game.mvp),
                        "mvp_team_logo": os.path.abspath(f"media/teams/{game.mvp.team.organization.logo_filename}")}

        html = html_file.read().format(**team_1_data, **team_2_data, **general_data)

        hti = Html2Image(output_path=folder_path)
        hti.screenshot(html_str=html, css_file="videos/html/post-match-statistics.css", save_as=filename)


def get_team_statistics_data(game: GameVod, team: Team, team_number: int, game_name: str) -> dict:
    """Return a dict that can be used to populate the HTML for the post match statistics image."""
    statistics_filename = getattr(game, f"team_{team_number}_statistics_filename")
    df = pd.read_csv(f"{game.match.create_unique_folder_path('statistics')}/{statistics_filename}")
    team_logo_filepath = os.path.abspath(f"media/teams/{team.organization.logo_filename}")

    if team_number == 1:
        result = "winner" if game.team_1_round_count > game.team_2_round_count else "loser"
    else:
        result = "winner" if game.team_2_round_count > game.team_1_round_count else "loser"

    score = df["kills"].sum() if game_name == "league-of-legends" else getattr(game, f"team_{team_number}_round_count")
    team_data = {f"team_{team_number}_name": str(team.organization), f"team_{team_number}_score": score,
                 f"team_{team_number}_result": result, f"team_{team_number}_logo": team_logo_filepath}

    if game_name == "counter-strike":
        columns = ["name", "kd", "plus_minus", "adr", "kast", "rating"]
    elif game_name == "valorant":
        df = df.drop("A", axis=1)
        df = df.drop("ADR", axis=1)
        columns = ["name", "r", "acs", "k", "d", "plus_minus", "kast", "hs_percent"]
    else:
        df = df.drop("position", axis=1)
        df = df.drop("gold", axis=1)
        columns = ["name", "kills", "deaths", "assists", "cs", "damage", "sight", "level"]

    for column_count, column in enumerate(columns):
        for value_count, value in enumerate(df.iloc[:, column_count].tolist()):
            team_data[f"team_{team_number}_player_{value_count + 1}_{column}"] = value

            if column == "plus_minus":
                sign = "plus" if value > 0 else "minus" if value < 0 else ""
                team_data[f"team_{team_number}_player_{value_count + 1}_sign"] = sign

                value = f"+{value}" if value > 0 else value
                team_data[f"team_{team_number}_player_{value_count + 1}_{column}"] = value

    return team_data
