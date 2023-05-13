import json

import requests
from bs4 import BeautifulSoup
from datetime import datetime

from scrapers.models import Tournament, Team, Match
from scrapers.scrapers.scraper import Scraper
from scrapers.types import MatchData


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
                    upcoming_matches.append(match)

        return upcoming_matches

    @staticmethod
    def scheduled_match_already_exists(match: dict) -> bool:
        """Return True if a Match object already exists for the given match."""
        start_datetime = datetime.strptime(match["scheduledAt"][:-5], "%Y-%m-%dT%H:%M:%S")
        return Match.objects.filter(start_datetime=start_datetime, team_1__name=match["homeTeam"]["name"],
                                    team_2__name=match["awayTeam"]["name"]).exists()

    @staticmethod
    def create_tournament(match: MatchData) -> Tournament:
        pass

    @staticmethod
    def create_team(team_name, team_id) -> Team:
        pass

    @staticmethod
    def create_scheduled_match(match: MatchData, tournament: Tournament, team_1: Team, team_2: Team) -> None:
        pass

    @staticmethod
    def is_match_finished(scheduled_match: Match) -> BeautifulSoup | None:
        pass

    @staticmethod
    def download_match_files(match:Match, html: BeautifulSoup) -> None:
        pass

    @staticmethod
    def extract_match_statistics(match: Match, html: BeautifulSoup) -> None:
        pass
