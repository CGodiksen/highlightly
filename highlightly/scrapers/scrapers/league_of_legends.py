import json
import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from scrapers.models import Tournament, Team, Match, Game
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

                    upcoming_matches.append(match)

        return upcoming_matches

    @staticmethod
    def extract_team_data(match_team_data: dict) -> TeamData:
        """Parse through the match team data to extract the team data that can be used to create a team object."""
        return {}

    @staticmethod
    def create_scheduled_match(match: dict, tournament: Tournament, team_1: Team, team_2: Team) -> None:
        pass

    @staticmethod
    def is_match_finished(scheduled_match: Match) -> BeautifulSoup | None:
        pass

    @staticmethod
    def download_match_files(match: Match, html: BeautifulSoup) -> None:
        pass

    @staticmethod
    def extract_match_statistics(match: Match, html: BeautifulSoup) -> None:
        pass
