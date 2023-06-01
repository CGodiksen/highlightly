import json
import logging
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from django_celery_beat.models import PeriodicTask

from scrapers.models import Match, Game, Organization, GameVod
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
            data["variables"]["year"] = datetime.now().year
            data["variables"]["month"] = datetime.now().month

            response = requests.post("https://esports.op.gg/matches/graphql", json=data)
            content = json.loads(response.content)

            # For each match in the response, extract data related to the match.
            for match in content["data"]["pagedAllMatches"]:
                if match["homeTeam"] is not None and match["awayTeam"] is not None:
                    # Only include the match if it is in one of the supported tournaments and takes place today.
                    short_name = match["tournament"]["serie"]["league"]["shortName"]
                    begin_at = datetime.strptime(str(match["beginAt"]).split(".")[0], "%Y-%m-%dT%H:%M:%S")

                    if short_name in self.included_tournaments and begin_at.date() == datetime.today().date():
                        match["team_1"] = match.pop("homeTeam")
                        match["team_2"] = match.pop("awayTeam")

                        match["game"] = Game.LEAGUE_OF_LEGENDS
                        match["tournament_name"] = match["tournament"]["serie"]["league"]["name"]
                        match["tournament_short_name"] = short_name
                        match["start_datetime"] = datetime.strptime(match.pop("scheduledAt")[:-5], "%Y-%m-%dT%H:%M:%S")

                        match["format"] = convert_number_of_games_to_format(match["numberOfGames"])
                        match["url"] = f"https://esports.op.gg/matches/{match['id']}"
                        match["tier"] = 1

                        stream = next((stream for stream in match["streams"] if stream["language"] == "en"), None)
                        match["stream_url"] = stream["rawUrl"] if stream else None

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

        if len(game_counts) == 2:
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

                # Since we assume the game has just started, delay the task to check the match status.
                new_task_start_time = datetime.now() + timedelta(minutes=30)
                PeriodicTask.objects.filter(name=f"Check {match} status").update(start_time=new_task_start_time)

                GameVod.objects.create(match=match, game_count=finished_game_count + 1, host=GameVod.Host.TWITCH,
                                       language="english")

            # Check if the most recently finished game has been marked as finished.
            if match.gamevod_set.filter(game_count=finished_game_count).exists():
                finished_game = match.gamevod_set.get(game_count=finished_game_count)
                if not finished_game.finished:
                    logging.info(f"Game {finished_game_count} for {match} is finished. Starting highlighting process.")

                    game_vod_updated = self.add_post_game_data(finished_game, soup, finished_game_count)

                    if game_vod_updated:
                        logging.info(f"Extracting game statistics for {finished_game}.")
                        self.extract_game_statistics(finished_game, soup)

                        finished_game.finished = True
                        finished_game.save(update_fields=["finished"])

    @staticmethod
    def add_post_game_data(game_vod: GameVod, html: BeautifulSoup, game_count: int) -> bool:
        """
        Extract match tournament data and update the game vod object with the post game data. If the post match
        data could not be found, return False, otherwise return True.
        """
        # Use the graphql endpoint to retrieve the finished game data.
        with open("../data/graphql/op_gg_match.json") as file:
            data = json.load(file)
            data["variables"]["matchId"] = game_vod.match.url.split("/")[-1]
            data["variables"]["set"] = game_count

            response = requests.post("https://esports.op.gg/matches/graphql", json=data)
            content = json.loads(response.content)
            match_data = content["data"]["gameByMatch"]

        if match_data is None or not match_data["finished"]:
            return False

        # TODO: Retrieve the tournament logo and tournament context of the match.
        # TODO: Update the game vod object using the data in the graphql response.

        return True

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
