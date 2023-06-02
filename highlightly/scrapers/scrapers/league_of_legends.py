import csv
import json
import logging
import os
import signal
import subprocess
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pytz
import requests
from bs4 import BeautifulSoup
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

from scrapers.models import Match, Game, Organization, GameVod, Tournament, Player
from scrapers.scrapers.scraper import Scraper
from scrapers.types import TeamData


class LeagueOfLegendsScraper(Scraper):
    """Webscraper that scrapes op.gg for upcoming League of Legends matches."""

    included_tournaments = ["LEC", "LPL", "LCK", "LCS"]

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

    def check_match_status(self, match: Match):
        """Check the current match status and start the highlighting process if a game is finished."""
        html = requests.get(url=match.url).text
        soup = BeautifulSoup(html, "html.parser")

        # Find the current number of finished games.
        game_counts = get_finished_games(match)
        finished_game_count = sum(game_counts)

        live_span = soup.find("span", class_="font-bold text-red-500")
        is_live = live_span is not None and live_span.text.strip().lower() == "live"

        if finished_game_count > 0 or is_live:
            # If it is the last game of the match, mark the match as finished and delete the related periodic task.
            bo1_finished = match.format == Match.Format.BEST_OF_1 and max(game_counts) == 1
            bo3_finished = match.format == Match.Format.BEST_OF_3 and max(game_counts) == 2
            bo5_finished = match.format == Match.Format.BEST_OF_5 and max(game_counts) == 3
            match_finished = bo1_finished or bo3_finished or bo5_finished

            if match_finished:
                logging.info(f"{match} is finished. Deleting the periodic task.")

                PeriodicTask.objects.filter(name=f"Check {match} status").delete()

                match.finished = True
                match.save()

            # If a new game has started, create an object for the game.
            if not match_finished and not match.gamevod_set.filter(game_count=finished_game_count + 1).exists():
                logging.info(f"Game {finished_game_count + 1} for {match} has started. Creating object for game.")

                # Start downloading the livestream related to the game. This stream is only stopped when the game is finished.
                stream_url = get_youtube_stream_url(match.tournament.short_name)

                vod_filename = f"game_{finished_game_count + 1}.mkv"
                vod_filepath = f"{match.create_unique_folder_path('vods')}/{vod_filename}"
                download_cmd = f"streamlink {stream_url} best -o {vod_filepath}"
                process = subprocess.Popen(download_cmd, stdout=subprocess.PIPE, shell=True, preexec_fn=os.setsid)

                # Since we assume the game has just started, delay the task to check the match status.
                new_task_start_time = timezone.localtime(timezone.now()) + timedelta(minutes=20)
                PeriodicTask.objects.filter(name=f"Check {match} status").update(start_time=new_task_start_time)

                GameVod.objects.create(match=match, game_count=finished_game_count + 1, host=GameVod.Host.YOUTUBE,
                                       language="english", process_id=process.pid, filename=vod_filename,
                                       map="Summoner's Rift", url=stream_url)

            # Check if the most recently finished game has been marked as finished.
            if match.gamevod_set.filter(game_count=finished_game_count).exists():
                finished_game = match.gamevod_set.get(game_count=finished_game_count)
                if not finished_game.finished:
                    logging.info(f"Game {finished_game_count} for {match} is finished. Starting highlighting process.")
                    match_data = retrieve_game_data(finished_game.match, finished_game.game_count)

                    self.add_post_game_data(match_data, finished_game)

                    # Stop the download of the livestream related to the game.
                    os.killpg(os.getpgid(finished_game.process_id), signal.SIGTERM)

                    logging.info(f"Extracting game statistics for {finished_game}.")
                    self.extract_game_statistics(finished_game, match_data)

                    finished_game.finished = True
                    finished_game.save(update_fields=["finished"])

    @staticmethod
    def add_post_game_data(match_data: dict, game_vod: GameVod) -> None:
        """Update the game vod object with the post game data."""
        # Set the winner of the match.
        if match_data["winner"]["name"] == game_vod.match.team_1.organization.name:
            game_vod.team_1_round_count = 1
            game_vod.team_2_round_count = 0
        else:
            game_vod.team_1_round_count = 0
            game_vod.team_2_round_count = 1

        # Set the actual start datetime of the game.
        begin_at = datetime.strptime(str(match_data["beginAt"]).split(".")[0], "%Y-%m-%dT%H:%M:%S")
        begin_at = pytz.utc.localize(begin_at)
        game_vod.start_datetime = begin_at.astimezone(pytz.timezone("Europe/Copenhagen"))

        game_vod.save()

    @staticmethod
    def extract_game_statistics(game_vod: GameVod, match_data: dict) -> None:
        """Extract and save statistics for the game. Also extract the MVP and the players photo."""
        team_data = defaultdict(list)
        statistics_folder_path = game_vod.match.create_unique_folder_path("statistics")
        headers = ["position", "name", "kills", "deaths", "assists", "cs", "damage", "sight", "level", "gold"]

        # Extract the player data from the match data.
        for player in match_data["players"]:
            name = f"{player['player']['firstName']} '{player['player']['nickName']}' {player['player']['lastName']}"

            team_data[player["team"]["name"]].append([player["position"], name, player["kills"], player["deaths"],
                                                      player["assists"], player["creepScore"],
                                                      player["totalDamageDealtToChampions"],
                                                      player["visionWardsBought"], player["level"],
                                                      player["goldEarned"]])

        # For each team, save a CSV file with the player data for the game.
        for team in [game_vod.match.team_1, game_vod.match.team_2]:
            team_name = team.organization.name.lower().replace(' ', '_')
            filename = f"map_{game_vod.game_count}_{team_name}.csv"

            with open(f"{statistics_folder_path}/{filename}", "w") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

                rows = team_data[team.organization.name]
                rows = [next(row for row in rows if row[0] == "top"), next(row for row in rows if row[0] == "jun"),
                        next(row for row in rows if row[0] == "mid"), next(row for row in rows if row[0] == "adc"),
                        next(row for row in rows if row[0] == "sup")]

                writer.writerows(rows)

            field_to_update = "team_1_statistics_filename" if game_vod.match.team_1 == team else "team_2_statistics_filename"
            setattr(game_vod, field_to_update, filename)
            game_vod.save()

        # Extract the MVP and save the player photo.
        mvp_data = next(player for player in match_data["players"] if player["mvpPoint"] == 1)
        player_url = f"https://esports.op.gg/players/{mvp_data['player']['id']}"

        if not Player.objects.filter(url=player_url).exists():
            mvp = extract_player_data(mvp_data, player_url)
        else:
            mvp = Player.objects.get(url=player_url)

        if mvp:
            game_vod.mvp = mvp
            game_vod.save()


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
    if Tournament.objects.filter(name=match_data["tournament_name"], logo_filename=logo_filename) is None:
        image_url = match_data["tournament"]["serie"]["league"]["imageUrl"]
        urllib.request.urlretrieve(image_url, f"media/tournaments/{logo_filename}")

    return logo_filename


def get_youtube_stream_url(channel_name: str):
    """Return the YouTube URL related to the livestream of the game."""
    api_key = os.environ["YOUTUBE_API_KEY"]
    base_url = "https://youtube.googleapis.com/youtube/v3/search"
    query = f"{channel_name} league of legends"

    response = requests.get(f"{base_url}?part=snippet&eventType=live&maxResults=5&q={query}&type=video&key={api_key}")

    return f"https://www.youtube.com/watch?v={json.loads(response.content)['items'][0]['id']['videoId']}"


def get_finished_games(match: Match) -> tuple[int, int]:
    """Return a tuple with the format (team_1_wins, team_2_wins)."""
    finished_games = match.gamevod_set.filter(finished=True)
    team_1_game_count = finished_games.filter(team_1_round_count=1).count()
    team_2_game_count = finished_games.filter(team_2_round_count=1).count()

    next_game_data = retrieve_game_data(match, finished_games.count() + 1)
    if next_game_data is not None and next_game_data["finished"]:
        if next_game_data["winner"]["name"] == match.team_1.organization.name:
            team_1_game_count += 1
        else:
            team_2_game_count += 1

    return team_1_game_count, team_2_game_count


def retrieve_game_data(match: Match, game_count: int) -> dict:
    """Use the graphql endpoint to retrieve the finished game data."""
    with open("../data/graphql/op_gg_match.json") as file:
        data = json.load(file)
        data["variables"]["matchId"] = match.url.split("/")[-1]
        data["variables"]["set"] = game_count

        response = requests.post("https://esports.op.gg/matches/graphql", json=data)
        content = json.loads(response.content)

        return content["data"]["gameByMatch"]


def extract_player_data(mvp_data: dict, url: str) -> Player:
    """Retrieve information about the player from the given URL and create a player object."""
    logging.info(f"Player in {url} does not already exist. Creating new player.")

    team = Organization.objects.get(name=mvp_data["team"]["name"]).teams.get(game=Game.LEAGUE_OF_LEGENDS)
    tag = mvp_data["player"]["nickName"]
    name = f"{mvp_data['player']['firstName']} {mvp_data['player']['lastName']}"

    profile_picture_filename = f"{team.organization.name.replace(' ', '-').lower()}-{tag.replace(' ', '-').lower()}.png"
    urllib.request.urlretrieve(mvp_data["player"]["imageUrl"], f"media/players/{profile_picture_filename}")

    return Player.objects.create(nationality=mvp_data["player"]["nationality"], tag=tag, name=name, url=url,
                                 team=team, profile_picture_filename=profile_picture_filename)
