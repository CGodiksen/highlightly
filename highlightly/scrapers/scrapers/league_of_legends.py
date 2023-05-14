import json
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from scrapers.models import Tournament, Team, Match
from scrapers.scrapers.scraper import Scraper


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
                    match["start_datetime"] = datetime.strptime(match.pop("scheduledAt")[:-5], "%Y-%m-%dT%H:%M:%S")
                    match["team_1"] = match.pop("homeTeam")
                    match["team_2"] = match.pop("awayTeam")

                    upcoming_matches.append(match)

        return upcoming_matches

    @staticmethod
    def create_tournament(match: dict) -> Tournament:
        pass

    @staticmethod
    def create_team(team_data: dict) -> Team:
        pass

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
