import json
import urllib.request
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from scrapers.models import Match, Game, Organization
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

        print(game_counts)
        print(finished_game_count)

def convert_number_of_games_to_format(number_of_games: int) -> Match.Format:
    """Convert the given number to the corresponding match format."""
    if number_of_games == 1:
        return Match.Format.BEST_OF_1
    elif number_of_games == 3:
        return Match.Format.BEST_OF_3
    else:
        return Match.Format.BEST_OF_5
