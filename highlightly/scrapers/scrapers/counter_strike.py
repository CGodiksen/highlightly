from datetime import datetime

import requests
from bs4 import BeautifulSoup, Tag

from scrapers.models import ScheduledMatch, Tournament, Team, Game
from scrapers.scrapers.scraper import Scraper
from scrapers.types import Match


class CounterStrikeScraper(Scraper):
    """Webscraper that scrapes hltv.org for upcoming Counter-Strike matches."""

    @staticmethod
    def list_upcoming_matches() -> list[Match]:
        upcoming_matches: list[Match] = []

        base_url = "https://cover.gg"
        html = requests.get(url=f"{base_url}/matches/current?tiers=s").text
        soup = BeautifulSoup(html, "html.parser")

        # Find the table with matches from today.
        today_table = soup.find(class_="table-body")
        rows: list[Tag] = today_table.find_all(class_="table-row table-row--upcoming")

        # For each row in the table, extract the teams, tournament, and match.
        for row in rows:
            cell_anchor = row.find(class_="c-global-match-link")
            team_divs = cell_anchor.find_all(class_="team-name")
            table_cell = row.find(class_="table-cell tournament")
            tournament_anchor = row.find(class_="o-link", href=True)

            team_1_name = team_divs[0].text
            team_2_name = team_divs[1].text

            match_url_postfix = cell_anchor["href"].replace("/prematch", "")
            match_url = f"{base_url}{match_url_postfix}"

            start_datetime = datetime.strptime(table_cell["date"][:-10], "%Y-%m-%dT%H:%M:%S")
            tier = convert_letter_tier_to_number_tier(table_cell["tier"])
            match_format = convert_number_to_format(int(table_cell["format"]))

            tournament_name: str = table_cell["tournament-name"]
            tournament_url = f"{base_url}{tournament_anchor['href']}"

            upcoming_matches.append({"url": match_url, "team_1": team_1_name, "team_2": team_2_name,
                                     "start_datetime": start_datetime, "tier": tier, "format": match_format,
                                     "tournament_name": tournament_name, "tournament_url": tournament_url})

        return upcoming_matches

    @staticmethod
    def create_tournament(match: Match) -> Tournament:
        tournament = Tournament.objects.filter(game=Game.COUNTER_STRIKE, name=match["tournament_name"])
        if tournament is None:
            # TODO: Retrieve the team logo.
            tournament = Tournament.objects.create(game=Game.COUNTER_STRIKE, name=match["tournament_name"],
                                                   logo_filename=None, url=match["tournament_url"])

        return tournament


    @staticmethod
    def create_teams(match: Match) -> (Team, Team):
        pass

    @staticmethod
    def create_scheduled_match(match: Match, tournament: Tournament, team_1: Team, team_2: Team) -> None:
        # TODO: Open the match url to find the tournament context.
        # TODO: Estimate the end datetime based on the start datetime and format.
        pass


def convert_letter_tier_to_number_tier(letter_tier: str) -> int:
    """Convert the given letter tier to the corresponding number tier."""
    conversion = {"s": 5, "a": 4, "b": 3, "c": 2, "d": 1}

    return conversion[letter_tier]


def convert_number_to_format(number: int) -> ScheduledMatch.Format:
    """Convert the given number to the corresponding match format."""
    if number == 1:
        return ScheduledMatch.Format.BEST_OF_1
    elif number == 3:
        return ScheduledMatch.Format.BEST_OF_3
    else:
        return ScheduledMatch.Format.BEST_OF_5


def get_hltv_team_url(team_name: str) -> str | None:
    """Search HLTV for the team name and find the url for the HLTV team page."""
    html = requests.get(url=f"https://www.hltv.org/search?query={team_name}").text
    soup = BeautifulSoup(html, "html.parser")

    # Find the table with the "Team" header.
    team_table_header = soup.find(class_="table-header", string="Team")
    team_row = team_table_header.find_parent().find_next_sibling() if team_table_header else None

    # Return the url in the first row of the team table.
    return f"https://www.hltv.org{team_row.find('a', href=True)['href']}" if team_row else None
