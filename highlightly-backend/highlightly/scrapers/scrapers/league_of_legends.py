import csv
import json
import logging
import os
import subprocess
import urllib.request
from datetime import datetime, timedelta
from json import JSONDecodeError
from pathlib import Path

import pytz
import requests
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

from scrapers.models import Match, Game, Organization, GameVod, Tournament, Player
from scrapers.scrapers.scraper import Scraper, finish_vod_stream_download
from scrapers.types import TeamData


class LeagueOfLegendsScraper(Scraper):
    """Webscraper that scrapes op.gg for upcoming League of Legends matches."""

    included_tournaments = ["LEC", "LPL", "LCK", "LCS", "CBLOL"]

    def list_upcoming_matches(self) -> list[dict]:
        """Use GraphQL to retrieve the upcoming matches from op.gg."""
        upcoming_matches: list[dict] = []

        # Use the graphql endpoint to retrieve the current scheduled match data.
        with open("../data/graphql/op_gg_upcoming_matches.json") as file:
            data = json.load(file)
            data["variables"]["year"] = timezone.localtime(timezone.now()).year
            data["variables"]["month"] = timezone.localtime(timezone.now()).month

            response = requests.post("https://esports.op.gg/matches/graphql", json=data)
            content = json.loads(response.content)

            # For each match in the response, extract data related to the match.
            for match in content["data"]["pagedAllMatches"]:
                if match["homeTeam"] is not None and match["awayTeam"] is not None:
                    # Only include the match if it is in one of the supported tournaments and takes place today.
                    short_name = match["tournament"]["serie"]["league"]["shortName"]

                    begin_at = datetime.strptime(str(match["beginAt"]).split(".")[0], "%Y-%m-%dT%H:%M:%S")
                    begin_at = pytz.utc.localize(begin_at)
                    start_datetime = begin_at.astimezone(pytz.timezone("Europe/Copenhagen"))

                    if short_name in self.included_tournaments and begin_at.date() == datetime.today().date():
                        match["team_1"] = match.pop("homeTeam")
                        match["team_2"] = match.pop("awayTeam")

                        match["game"] = Game.LEAGUE_OF_LEGENDS
                        match["start_datetime"] = start_datetime

                        match["format"] = convert_number_of_games_to_format(match["numberOfGames"])
                        match["url"] = f"https://esports.op.gg/matches/{match['id']}"
                        match["tier"] = 1

                        stream = next((stream for stream in match["streams"] if stream["language"] == "en"), None)
                        match["stream_url"] = stream["rawUrl"] if stream else None

                        # Extract information about the tournament of the match.
                        match["tournament_name"] = match["tournament"]["serie"]["league"]["name"]
                        match["tournament_context"] = match["tournament"]["name"]
                        match["tournament_short_name"] = short_name
                        match["tournament_logo_filename"] = save_tournament_logo(match)

                        upcoming_matches.append(match)

        return upcoming_matches

    @staticmethod
    def extract_team_data(match_team_data: dict, organization: Organization) -> TeamData:
        """Parse through the match team data to extract the team data that can be used to create a team object."""
        team_url = f"https://esports.op.gg/teams/{match_team_data['id']}"

        if organization.logo_filename is None:
            logo_filename = f"{match_team_data['name'].replace(' ', '_')}.png"
            Path("media/teams").mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(match_team_data["imageUrlDarkMode"], f"media/teams/{logo_filename}")

            organization.logo_filename = logo_filename
            organization.save()

        return {"url": team_url, "nationality": match_team_data["nationality"], "ranking": None}

    @staticmethod
    def check_match_status(match: Match) -> None:
        """Check the current match status and start the highlighting process if a game is finished."""
        logging.info(f"Checking the status of {match}.")

        # Check that the previous matches in the same tournament are done first.
        previous_matches = Match.objects.filter(tournament=match.tournament, start_datetime__lt=match.start_datetime,
                                                finished=False)

        if previous_matches.count() > 0:
            logging.info(f"{previous_matches.count()} previous matches needs to finish before {match}.")
            return None

        match_data = get_match_data(match)

        # Find the current number of finished games.
        game_counts, next_game_data = get_match_data_finished_game_counts(match, match_data)
        finished_game_count = sum(game_counts)

        if finished_game_count > 0 or match_data["lifecycle"] == "live":
            bo1_finished = match.format == Match.Format.BEST_OF_1 and max(game_counts) == 1
            bo3_finished = match.format == Match.Format.BEST_OF_3 and max(game_counts) == 2
            bo5_finished = match.format == Match.Format.BEST_OF_5 and max(game_counts) == 3
            match_finished = bo1_finished or bo3_finished or bo5_finished

            # If a new game has started, create an object for the game.
            if not match_finished and not match.gamevod_set.filter(game_count=finished_game_count + 1).exists():
                logging.info(f"Game {finished_game_count + 1} for {match} has started. Creating object for game.")
                handle_game_started(match, finished_game_count)

            # Check if the most recently finished game has been marked as finished.
            if match.gamevod_set.filter(game_count=finished_game_count).exists() and next_game_data is not None:
                finished_game = match.gamevod_set.get(game_count=finished_game_count)
                if not finished_game.finished:
                    logging.info(f"Game {finished_game_count} for {match} is finished. Starting highlighting process.")
                    handle_game_finished(finished_game, next_game_data, match, match_finished)
        else:
            logging.info(f"{match} has not started yet.")


def convert_number_of_games_to_format(number_of_games: int) -> Match.Format:
    """Convert the given number to the corresponding match format."""
    if number_of_games == 1:
        return Match.Format.BEST_OF_1
    elif number_of_games == 3:
        return Match.Format.BEST_OF_3
    else:
        return Match.Format.BEST_OF_5


def save_tournament_logo(match_data: dict) -> str:
    """if the tournament of the match does not already have a logo, save the logo and return the filename."""
    Path("media/tournaments").mkdir(parents=True, exist_ok=True)
    logo_filename = f"{match_data['tournament_name'].replace(' ', '_')}.png"

    # Only download the tournament logo if it does not already exist.
    if not Tournament.objects.filter(name=match_data["tournament_name"], logo_filename=logo_filename).exists():
        image_url = match_data["tournament"]["serie"]["league"]["imageUrl"]
        urllib.request.urlretrieve(image_url, f"media/tournaments/{logo_filename}")

    return logo_filename


def get_match_data(match: Match) -> dict:
    """Return the match data from the 1337pro.com matches that correspond to the given match object."""
    today = timezone.localtime(timezone.now())
    start_timestamp = int((datetime(today.year, today.month, today.day)).timestamp() * 1e3)
    end_timestamp = int((datetime(today.year, today.month, today.day, 23, 59, 59)).timestamp() * 1e3)

    url = f"https://neptune.1337pro.com/series/grouped/all-and-live?start_after={start_timestamp}&start_before={end_timestamp}"
    headers = {"Accept": "application/vnd.neptune+json; version=1"}
    html = requests.get(url=url, headers=headers).text

    matches: dict = json.loads(html)
    league_of_legends_matches = [m for m in matches["items"] if
                                 len(m["participants"]) == 2 and m["participants"][0]["game_id"] == 2]

    for m in league_of_legends_matches:
        team_names = [p["team_name"] for p in m["participants"]]
        team_1_matches = team_names[0].lower() in [name.lower() for name in match.team_1.organization.get_names()]
        team_2_matches = team_names[1].lower() in [name.lower() for name in match.team_2.organization.get_names()]

        if team_1_matches and team_2_matches:
            return m


def get_match_data_finished_game_counts(match, match_data: dict) -> tuple[tuple[int, int], dict | None]:
    """Return a tuple with the format ((team_1_wins, team_2_wins), next_game_data)."""
    team_1_score = 0
    team_2_score = 0

    for game in match.gamevod_set.filter(finished=True):
        if game.team_1_round_count > game.team_2_round_count:
            team_1_score += 1
        else:
            team_2_score += 1

    # Check if the next game is finished and return the game data if so.
    next_game_data = get_post_game_data(match_data, team_1_score + team_2_score + 1)
    if next_game_data and "match" in next_game_data and next_game_data["match"]["phase"] == "game-over":
        team_1 = next_game_data["teams"]["home"]
        if team_1["is_winner"] is not None and team_1["is_winner"]:
            team_1_score += 1
        else:
            team_2_score += 1
    else:
        next_game_data = None

    return (team_1_score, team_2_score), next_game_data


def handle_game_started(match: Match, finished_game_count: int) -> None:
    """Start downloading the stream related to the game and create an object to save game data."""
    # Start downloading the livestream related to the game. This stream is only stopped when the game is finished.
    stream_url = f"https://www.twitch.tv/{match.tournament.short_name.lower()}"

    logging.info(f"Connecting to stream from {stream_url} to download VOD.")

    vod_filename = f"game_{finished_game_count + 1}.mkv"
    vod_filepath = f"{match.create_unique_folder_path('vods')}/{vod_filename}"

    download_cmd = f"streamlink {stream_url} best -O | ffmpeg -fflags +discardcorrupt -re -i pipe:0 -filter:v scale=1920:-1 -c:a copy {vod_filepath}"
    process = subprocess.Popen(download_cmd, stdout=subprocess.PIPE, shell=True, preexec_fn=os.setsid)

    # Since we assume the game has just started, delay the task to check the match status.
    new_task_start_time = timezone.localtime(timezone.now()) + timedelta(minutes=20)
    PeriodicTask.objects.filter(name=f"Check {match} status").update(start_time=new_task_start_time)

    GameVod.objects.create(match=match, game_count=finished_game_count + 1, host=GameVod.Host.TWITCH,
                           language="english", start_datetime=timezone.localtime(timezone.now()),
                           process_id=process.pid, filename=vod_filename, map="Summoner's Rift",
                           url=stream_url)


def handle_game_finished(finished_game: GameVod, game_data: dict, match: Match, match_finished: bool) -> None:
    """Stop the download of the livestream, add post game data to game vod object, and extract game statistics."""
    finish_vod_stream_download(finished_game)

    try:
        add_post_game_data(game_data, finished_game)

        logging.info(f"Extracting game statistics for {finished_game}.")
        extract_game_statistics(game_data, finished_game)

        # If it is the last game of the match, mark the match as finished and delete the related periodic task.
        if match_finished:
            logging.info(f"{match} is finished. Deleting the periodic task.")
            PeriodicTask.objects.filter(name=f"Check {match} status").delete()

            match.finished = True
            match.save()

        finished_game.finished = True
        finished_game.save(update_fields=["finished"])
    except JSONDecodeError as e:
        logging.error(f"Game data for {finished_game} could not be retrieved: {e}")


def get_post_game_data(match_data: dict, game_count: int) -> dict:
    """Return the detailed game data related to a specific finished game of the match in the given match data."""
    try:
        game_id = match_data["matches"][game_count - 1]["id"]

        url = f"https://neptune.1337pro.com/matches/{game_id}/summary?seriesId={match_data['id']}"
        headers = {"Accept": "application/vnd.neptune+json; version=1"}
        html = requests.get(url=url, headers=headers).text

        return json.loads(html) if len(html) > 0 else {}
    except IndexError:
        return {}


def add_post_game_data(game_data: dict, game_vod: GameVod) -> None:
    """Update the game vod object with the post game data."""
    team_1 = game_data["teams"]["home"]

    # Set the winner of the match.
    if team_1["is_winner"] is not None and team_1["is_winner"]:
        game_vod.team_1_round_count = 1
        game_vod.team_2_round_count = 0
    else:
        game_vod.team_1_round_count = 0
        game_vod.team_2_round_count = 1

    game_vod.save()


def extract_game_statistics(game_data: dict, game_vod: GameVod) -> None:
    """Extract and save statistics for the game. Also extract the MVP and the players photo."""
    team_rows, mvp = get_game_team_statistics(game_data, game_vod)

    statistics_folder_path = game_vod.match.create_unique_folder_path("statistics")
    headers = ["name", "kills", "deaths", "assists", "cs", "cs_minute", "ratio"]

    # For each team, save a CSV file with the player data for the game.
    for team, team_data in [(game_vod.match.team_1, team_rows[0]), (game_vod.match.team_2, team_rows[1])]:
        team_name = team.organization.name.lower().replace(' ', '_')
        filename = f"map_{game_vod.game_count}_{team_name}.csv"

        with open(f"{statistics_folder_path}/{filename}", "w") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(team_data)

        field_to_update = "team_1_statistics_filename" if game_vod.match.team_1 == team else "team_2_statistics_filename"
        setattr(game_vod, field_to_update, filename)
        game_vod.save()

    # Extract the MVP and save the player profile picture if possible.
    game_mvp = Player.objects.filter(tag=mvp["tag"], name=mvp["name"]).first()

    if game_mvp is None:
        logging.info(f"Player with tag '{mvp['tag']}' does not already exist. Creating new player.")

        if mvp["profile_picture_url"] is not None:
            r = requests.get(mvp["profile_picture_url"])
            profile_picture_filename = f"{mvp['team'].organization.name.replace(' ', '-').lower()}-{mvp['tag'].replace(' ', '-').lower()}.png"
            with open(f"media/players/{profile_picture_filename}", 'wb') as outfile:
                outfile.write(r.content)
        else:
            profile_picture_filename = "default.png"

        game_mvp = Player.objects.create(nationality=mvp["nationality"], tag=mvp["tag"], name=mvp["name"], url="",
                                         team=mvp["team"], profile_picture_filename=profile_picture_filename)

    game_vod.mvp = game_mvp
    game_vod.save()


def get_game_team_statistics(game_data: dict, game_vod: GameVod) -> tuple[list[list], dict]:
    """Find the per-player statistics for each team in the given game and the MVP of the entire game."""
    game_duration_minutes = (game_data["match"]["timeline"]["clock"]["milliseconds"] / 1000) / 60

    team_1 = game_data["teams"]["home"]
    team_2 = game_data["teams"]["away"]

    url = f"https://neptune.1337pro.com/rosters?ids={team_1['roster']['id']},{team_2['roster']['id']}"
    headers = {"Accept": "application/vnd.neptune+json; version=1"}
    html = requests.get(url=url, headers=headers).text
    rosters = json.loads(html)

    team_1_roster = next(roster for roster in rosters if roster["id"] == team_1['roster']['id'])
    team_2_roster = next(roster for roster in rosters if roster["id"] == team_2['roster']['id'])

    mvp = {"ratio": -1, "tag": None, "name": None, "team": None, "nationality": None}

    team_rows = []
    for team, roster in [(team_1, team_1_roster), (team_2, team_2_roster)]:
        team_data = []

        for player in team["players"]:
            roster_player = next(p for p in roster["players"] if p["id"] == player["id"])
            name = f"{roster_player['first_name']} '{roster_player['nick_name']}' {roster_player['last_name']}"
            ratio = (player["kills"]["total"] + player["assists"]["total"]) / max(player["deaths"]["total"], 1)

            # Set the MVP to the player with the highest KDA ratio.
            if ratio > mvp["ratio"]:
                mvp_team = game_vod.match.team_1 if team == team_1 else game_vod.match.team_2
                image_url = roster_player["images"][0]["url"] if len(roster_player["images"]) > 0 else None

                mvp = {"ratio": ratio, "tag": roster_player["nick_name"], "team": mvp_team,
                       "name": f"{roster_player['first_name']} {roster_player['last_name']}",
                       "nationality": roster_player["country"]["name"], "profile_picture_url": image_url}

            cs = player["creeps"]["total"]["kills"]
            team_data.append([name, player["kills"]["total"], player["deaths"]["total"], player["assists"]["total"],
                              cs, round(cs / game_duration_minutes, 1), round(ratio, 2)])

        team_rows.append(team_data)

    return team_rows, mvp
