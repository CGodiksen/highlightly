import os
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup, Tag
from serpapi import GoogleSearch

from scrapers.models import ScheduledMatch, Tournament, Team, Game
from scrapers.scrapers.scraper import Scraper
from scrapers.types import MatchData, TournamentData


class CounterStrikeScraper(Scraper):
    """Webscraper that scrapes hltv.org for upcoming Counter-Strike matches."""

    @staticmethod
    def list_upcoming_matches() -> list[MatchData]:
        upcoming_matches: list[MatchData] = []

        base_url = "https://cover.gg"
        html = requests.get(url=f"{base_url}/matches/current?tiers=s").text
        soup = BeautifulSoup(html, "html.parser")

        # Find the table with matches from today.
        today_table = soup.find(class_="table-body")
        rows: list[Tag] = today_table.find_all(class_="table-row table-row--upcoming")

        # For each row in the table, extract the teams, tournament, and match.
        for row in rows:
            match = extract_match_data(row, base_url)

            # Ignore the match if it currently still contains a "TBD" team.
            if match["team_1"] != "TBD" and match["team_2"] != "TBD":
                upcoming_matches.append(match)

        return upcoming_matches

    @staticmethod
    def create_tournament(match: MatchData) -> Tournament:
        tournament = Tournament.objects.filter(game=Game.COUNTER_STRIKE, name=match["tournament_name"]).first()
        if tournament is None:
            tournament_url = get_liquipedia_tournament_url(match["tournament_name"])
            html = requests.get(url=tournament_url).text
            soup = BeautifulSoup(html, "html.parser")

            # Extract the tournament data from the HTML.
            data = extract_tournament_data(soup)

            # TODO: Download the image from the logo url and save the name of the image file.
            logo_filename = None

            tournament = Tournament.objects.create(game=Game.COUNTER_STRIKE, name=match["tournament_name"],
                                                   url=tournament_url, start_date=data["start_date"],
                                                   end_date=data["end_date"], prize_pool_us_dollars=data["prize_pool"],
                                                   first_place_prize_us_dollars=data["first_place_prize"],
                                                   location=data["location"], tier=data["tier"], type=data["type"],
                                                   logo_filename=logo_filename)

        return tournament

    @staticmethod
    def create_team(match: MatchData, team_name) -> Team:
        team = Team.objects.filter(game=Game.COUNTER_STRIKE, name=team_name).first()
        if team is None:
            # Find the HLTV team url using the name of the team.
            team_url = get_hltv_team_url(team_name)

            # Extract the nationality and world ranking of the team.
            html = requests.get(url=team_url).text
            soup = BeautifulSoup(html, "html.parser")

            nationality = soup.find("div", class_="team-country text-ellipsis").text.strip()
            ranking = int(soup.find("b", text="World ranking").find_next_sibling().text[1:])

            # Retrieve the team logo if possible.
            logo_filename = get_team_logo_filepath(team_url)

            team = Team.objects.create(game=Game.COUNTER_STRIKE, name=team_name, logo_filename=logo_filename,
                                       nationality=nationality, ranking=ranking, url=team_url)

        return team

    @staticmethod
    def create_scheduled_match(match: MatchData, tournament: Tournament, team_1: Team, team_2: Team) -> None:
        # Open the match url to find the tournament context.
        html = requests.get(url=match["url"]).text
        soup = BeautifulSoup(html, "html.parser")

        tournament_context = soup.find("a", class_="stage", href=True).text

        # Estimate the end datetime based on the start datetime and format.
        minimum_minutes = convert_format_to_minimum_time(match["format"])
        estimated_end_datetime = match["start_datetime"] + timedelta(minutes=minimum_minutes)

        # Automatically mark the scheduled game for highlight creation if it is tier 4 or higher.
        create_video = match["tier"] >= 4

        ScheduledMatch.objects.create(team_1=team_1, team_2=team_2, tournament=tournament, format=match["format"],
                                      tournament_context=tournament_context, tier=match["tier"], url=match["url"],
                                      start_datetime=match["start_datetime"], create_video=create_video,
                                      estimated_end_datetime=estimated_end_datetime)


def extract_match_data(html: Tag, base_url: str) -> MatchData:
    """Given the HTML for a row in the upcoming matches table, extract the data for a match."""
    cell_anchor = html.find(class_="c-global-match-link")
    team_divs = cell_anchor.find_all(class_="team-name")
    table_cell = html.find(class_="table-cell tournament")

    team_1_name = team_divs[0].text
    team_2_name = team_divs[1].text

    match_url_postfix = cell_anchor["href"].replace("/prematch", "")
    match_url = f"{base_url}{match_url_postfix}"

    start_datetime = datetime.strptime(table_cell["date"][:-10], "%Y-%m-%dT%H:%M:%S")
    tier = convert_letter_tier_to_number_tier(table_cell["tier"])
    match_format = convert_number_to_format(int(table_cell["format"]))

    tournament_name: str = table_cell["tournament-name"]

    return {"url": match_url, "team_1": team_1_name, "team_2": team_2_name, "start_datetime": start_datetime,
            "tier": tier, "format": match_format, "tournament_name": tournament_name}


def extract_tournament_data(html: BeautifulSoup) -> TournamentData:
    """Given the HTML for the tournaments liquipedia wiki page, extract the data for the tournament."""
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


def convert_format_to_minimum_time(match_format: ScheduledMatch.Format) -> int:
    """
    Return the minimum number of minutes required to complete a match with the given format. We assume each game takes
    at least 30 minutes and that there is at least 5 minutes of break between games.
    """
    if match_format == ScheduledMatch.Format.BEST_OF_1:
        return 1 * 30
    elif match_format == ScheduledMatch.Format.BEST_OF_3:
        return (2 * 30) + 5
    else:
        return (3 * 30) + 10


def get_hltv_team_url(team_name: str) -> str | None:
    """Search HLTV for the team name and find the url for the HLTV team page."""
    html = requests.get(url=f"https://www.hltv.org/search?query={team_name}").text
    soup = BeautifulSoup(html, "html.parser")

    # Find the table with the "Team" header.
    team_table_header = soup.find(class_="table-header", string="Team")
    team_row = team_table_header.find_parent().find_next_sibling() if team_table_header else None

    # Return the url in the first row of the team table.
    return f"https://www.hltv.org{team_row.find('a', href=True)['href']}" if team_row else None


def get_liquipedia_tournament_url(tournament_name: str) -> str | None:
    """
    Attempt to retrieve the url for the tournaments liquipedia wiki page. Since the liquipedia wiki search is faulty,
    use Google Search to find the corresponding liquipedia page.
    """
    # Since the liquipedia wiki search is faulty, use Google Search to find the corresponding liquipedia page.
    search = GoogleSearch({
        "engine": "google",
        "api_key": os.environ["SERP_API_KEY"],
        "q": f"{tournament_name} site:https://liquipedia.net/counterstrike",
        "as_qdr": "w2"
    })
    result = search.get_dict()

    return result["organic_results"][0]["link"] if len(result["organic_results"]) > 0 else None


def get_team_logo_filepath(team_url: str) -> str | None:
    """
    Attempt to retrieve the logo from the HLTV team page, if not possible, attempt to retrieve the team logo from
    the liquipedia wiki. If the logo is retrieved, return the path to the file. If neither method works, return None.
    """
    # TODO: Retrieve the team logo from the HLTV team page.
    # TODO: If the logo is too small or could not be retrieved at all, attempt to retrieve it from liquipedia.

    return None
