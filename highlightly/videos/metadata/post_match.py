import re

import pandas as pd

from scrapers.models import Match
from videos.models import VideoMetadata


def add_post_match_video_metadata(match: Match):
    """
    Add metadata to the video metadata that can only be extracted once the match is finished. This includes
    statistics about the performance of each player during the match, the tournament context, the tournament logo,
    and a frame from the match for the thumbnail.
    """
    video_metadata = VideoMetadata.objects.get(match=match)
    new_tags = video_metadata.tags
    new_description = video_metadata.description

    # Add the tournament context to the description and tags.
    new_description = new_description.replace("TOURNAMENT_CONTEXT", match.tournament_context)
    new_tags.append(match.tournament_context)

    # Add players to description and tags.
    statistics_folder_path = f"media/statistics/{match.create_unique_folder_path()}"
    team_1_statistics = pd.read_csv(f"{statistics_folder_path}/{match.team_1_statistics_filename}")
    team_2_statistics = pd.read_csv(f"{statistics_folder_path}/{match.team_2_statistics_filename}")

    team_1_in_game_names = get_team_in_game_names(team_1_statistics)
    team_2_in_game_names = get_team_in_game_names(team_2_statistics)

    new_description = new_description.replace("TEAM_1_PLAYERS", ", ".join(team_1_in_game_names))
    new_description = new_description.replace("TEAM_2_PLAYERS", ", ".join(team_2_in_game_names))
    new_tags.extend(team_1_in_game_names)
    new_tags.extend(team_2_in_game_names)

    # TODO: Add credit to where the VOD is from to the description.
    # TODO: Add a frame from the match and the tournament logo to the thumbnail.
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
