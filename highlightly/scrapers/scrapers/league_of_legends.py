import json
import logging
import os
import subprocess
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep

import pytz
import requests
from bs4 import BeautifulSoup
from django_celery_beat.models import PeriodicTask

from scrapers.models import Match, Game, Organization, GameVod
from scrapers.scrapers.scraper import Scraper
from scrapers.types import TeamData


class LeagueOfLegendsScraper(Scraper):
    """Webscraper that scrapes op.gg for upcoming League of Legends matches."""

    @staticmethod
    def list_upcoming_matches() -> list[dict]:
        """Use GraphQL to retrieve the upcoming matches from op.gg."""
        upcoming_matches: list[dict] = []

        # Use the graphql endpoint to retrieve the current scheduled match data.
        with open("../data/graphql/op_gg_upcoming_matches.json") as file:
            data = json.load(file)
            data["variables"]["year"] = datetime.now().year
            data["variables"]["month"] = datetime.now().month

            response = requests.post("https://esports.op.gg/matches/graphql", json=data)
            content = json.loads(response.content)

            # For each match in the response, extract data related to the match.
            for match in content["data"]["pagedAllMatches"]:
                if match["homeTeam"] is not None and match["awayTeam"] is not None:
                    match["team_1"] = match.pop("homeTeam")
                    match["team_2"] = match.pop("awayTeam")

                    match["game"] = Game.LEAGUE_OF_LEGENDS
                    match["tournament_name"] = match["tournament"]["serie"]["league"]["name"]
                    match["start_datetime"] = datetime.strptime(match.pop("scheduledAt")[:-5], "%Y-%m-%dT%H:%M:%S")

                    match["format"] = convert_number_of_games_to_format(match["numberOfGames"])
                    match["url"] = f"https://esports.op.gg/matches/{match['id']}"
                    match["tier"] = 1

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
        score_divs = soup.findAll("div", class_="m-1 flex items-center justify-center h-9 w-9")
        game_counts = [int(div.text.strip()) for div in score_divs if div.text.strip().isdigit()]
        finished_game_count = sum(game_counts)

        if finished_game_count > 0:
            # If it is the last game of the match, mark the match as finished and delete the related periodic task.
            bo1_finished = match.format == Match.Format.BEST_OF_1 and max(game_counts) == 1
            bo3_finished = match.format == Match.Format.BEST_OF_3 and max(game_counts) == 2
            bo5_finished = match.format == Match.Format.BEST_OF_5 and max(game_counts) == 3
            if bo1_finished or bo3_finished or bo5_finished:
                logging.info(f"{match} is finished. Deleting the periodic task.")

                PeriodicTask.objects.filter(name=f"Check {match} status").delete()

                match.finished = True
                match.save()

            # Check if the most recently finished game exists and if not, create a game vod and start highlighting.
            if not match.gamevod_set.filter(game_count=finished_game_count).exists():
                logging.info(f"Game {finished_game_count} for {match} is finished. Starting highlighting process.")

                finished_game = self.download_game_files(match, soup, finished_game_count)

                if finished_game is not None:
                    logging.info(f"Extracting game statistics for {finished_game}.")
                    self.extract_game_statistics(finished_game, soup)

                    finished_game.finished = True
                    finished_game.save(update_fields=["finished"])

    @staticmethod
    def download_game_files(match: Match, html: BeautifulSoup, game_count: int) -> GameVod:
        """Download the VOD for the game and create game vod object."""
        datetime_format = "%Y-%m-%dT%H:%M:%S"

        # Use the graphql endpoint to retrieve the finished game data.
        with open("../data/graphql/op_gg_match.json") as file:
            data = json.load(file)
            data["variables"]["matchId"] = match.url.split("/")[-1]
            data["variables"]["set"] = game_count

            response = requests.post("https://esports.op.gg/matches/graphql", json=data)
            content = json.loads(response.content)
            match_data = content["data"]["gameByMatch"]

        if match_data is None or not match_data["finished"]:
            return None

        # TODO: Retrieve the tournament logo and tournament context of the match.

        # Find the URL of the current YouTube livestream related to the game.
        stream_url = get_youtube_stream_url("lpl")

        # TODO: Download the full game from the stream using youtube-dl.

        # TODO: Create a game vod object using the data in the graphql response.


    def extract_game_statistics(self, game: GameVod, html: BeautifulSoup) -> None:
        """Extract and save statistics for the game. Also extract the MVP and the players photo."""
        pass


def convert_number_of_games_to_format(number_of_games: int) -> Match.Format:
    """Convert the given number to the corresponding match format."""
    if number_of_games == 1:
        return Match.Format.BEST_OF_1
    elif number_of_games == 3:
        return Match.Format.BEST_OF_3
    else:
        return Match.Format.BEST_OF_5


def get_twitch_video(match_data: dict, stream_url: str, datetime_format: str) -> dict:
    """Return the Twitch video related to the game."""
    tz = pytz.timezone("Europe/Copenhagen")

    match_end_datetime = datetime.strptime(str(match_data["endAt"]).split(".")[0], datetime_format)

    # Since Twitch videos have a delay compared to the livestream, keep checking until the video is updated.
    for _ in range(10):
        # Find the latest video from the stream which should be the video with the for the game.
        list_videos_cmd = f"twitch-dl videos -j {stream_url.split('/')[-1]}"
        result = subprocess.run(list_videos_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        video = json.loads(result.stdout.decode())["videos"][0]

        vod_started_at = datetime.strptime(video["publishedAt"], "%Y-%m-%dT%H:%M:%SZ").astimezone(tz)
        vod_ended_at = vod_started_at + timedelta(seconds=int(video["lengthSeconds"]))

        logging.info(f"Game ended at {match_end_datetime}. Found Twitch video that ends at {vod_ended_at}: {video}.")

        if vod_ended_at > match_end_datetime:
            return video
        else:
            sleep(60)


def get_youtube_stream_url(channel_name: str):
    """Return the YouTube URL related to the livestream of the game."""
    api_key = os.environ["YOUTUBE_API_KEY"]
    base_url = "https://youtube.googleapis.com/youtube/v3/search"
    query = f"{channel_name} league of legends"

    response = requests.get(f"{base_url}?part=snippet&eventType=live&maxResults=5&q={query}&type=video&key={api_key}")

    return f"https://www.youtube.com/watch?v={json.loads(response.content)['items'][0]['id']['videoId']}"
