import os
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag
from cairosvg import svg2png
from serpapi import GoogleSearch

from scrapers.models import ScheduledMatch, Tournament, Team, Game
from scrapers.scrapers.scraper import Scraper
from scrapers.types import MatchData, TournamentData
from util.file_util import download_file_from_url


class CounterStrikeScraper(Scraper):
    """Webscraper that scrapes hltv.org for upcoming Counter-Strike matches."""

    @staticmethod
    def list_upcoming_matches() -> list[MatchData]:
        upcoming_matches: list[MatchData] = []

        base_url = "https://www.hltv.org"
        soup = get_protected_page_html(f"{base_url}/matches", "matches_page.txt")

        # Find the table with matches from today.
        upcoming_matches_tables = soup.find_all("div", class_="upcomingMatchesSection")
        rows: list[Tag] = upcoming_matches_tables[0].find_all("div", class_="upcomingMatch")

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

            # Download the image from the logo url and save the name of the image file.
            Path("media/tournaments").mkdir(parents=True, exist_ok=True)
            logo_filename = f"{match['tournament_name'].replace(' ', '_')}.png"
            download_file_from_url(data["logo_url"], f"tournaments/{logo_filename}")

            tournament = Tournament.objects.create(game=Game.COUNTER_STRIKE, name=match["tournament_name"],
                                                   url=tournament_url, start_date=data["start_date"],
                                                   end_date=data["end_date"], prize_pool_us_dollars=data["prize_pool"],
                                                   first_place_prize_us_dollars=data["first_place_prize"],
                                                   location=data["location"], tier=data["tier"], type=data["type"],
                                                   logo_filename=logo_filename)

        return tournament

    @staticmethod
    def create_team(team_name) -> Team:
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
            logo_filename = get_team_logo_filepath(team_url, team_name)

            team = Team.objects.create(game=Game.COUNTER_STRIKE, name=team_name, logo_filename=logo_filename,
                                       nationality=nationality, ranking=ranking, url=team_url)

        return team

    @staticmethod
    def create_scheduled_match(match: MatchData, tournament: Tournament, team_1: Team, team_2: Team) -> None:
        # Open the match url to find the tournament context.
        html = requests.get(url=match["url"]).text
        soup = BeautifulSoup(html, "html.parser")

        # TODO: Maybe wait with this until we retrieve the post game data.
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


# TODO: Change this function back when done with testing.
def get_protected_page_html(protected_url: str, test=None) -> BeautifulSoup:
    """Return the HTML for the given URL. This bypasses cloudflare protections."""
    if test:
        with open(f"media/test/{test}", "r") as f:
            html = f.read()
    else:
        base_url = " https://api.scrapingant.com"
        safe_protected_url = urllib.parse.quote_plus(protected_url)
        url = f"{base_url}/v2/general?url={safe_protected_url}&x-api-key={os.environ['SCRAPING_API_KEY']}"

        html = requests.get(url=url).text

    return BeautifulSoup(html, "html.parser")


def extract_match_data(html: Tag, base_url: str) -> MatchData:
    """Given the HTML for a row in the upcoming matches table, extract the data for a match."""
    team_1_name = extract_team_name(html, 1)
    team_2_name = extract_team_name(html, 2)

    match_url_postfix = html.find("a", class_="match a-reset")["href"]
    match_url = f"{base_url}{match_url_postfix}"

    unix_timestamp = int(html.find("div", class_="matchTime")["data-unix"])
    start_datetime = datetime.utcfromtimestamp(unix_timestamp / 1000)
    match_format = convert_label_to_format(html.find("div", class_="matchMeta").text)

    tier = 5 - len(html.find("div", class_="matchRating").find_all("i", class_="fa fa-star faded"))

    tournament_name: str = html.find("div", class_="matchEventName").text
    tournament_logo_url: str = html.find("img", class_="matchEventLogo")["src"]

    return {"url": match_url, "team_1": team_1_name, "team_2": team_2_name, "start_datetime": start_datetime,
            "tier": tier, "format": match_format, "tournament_name": tournament_name,
            "tournament_logo_url": tournament_logo_url}


def extract_team_name(html: Tag, team_number: int) -> str:
    """Return the formatted name of either team 1 or team 2."""
    team_div = html.find("div", class_=f"matchTeam team{team_number}")
    team_name = team_div.text if team_div.find("div", class_="matchTeamLogoContainer") is not None else "TBD"

    return team_name.replace("\n", "")


def extract_tournament_data(html: BeautifulSoup) -> TournamentData:
    """Given the HTML for the tournaments liquipedia wiki page, extract the data for the tournament."""
    start_date = datetime.strptime(get_tournament_table_data(html, "Start Date:"), "%Y-%m-%d").date()
    end_date = datetime.strptime(get_tournament_table_data(html, "End Date:"), "%Y-%m-%d").date()

    prize_pool = get_tournament_table_data(html, "Prize Pool:").split("\xa0")[0]
    location = get_tournament_table_data(html, "Location:").strip()
    tier = convert_letter_tier_to_number_tier(get_tournament_table_data(html, "Liquipedia Tier:").lower())
    type = Tournament.Type(get_tournament_table_data(html, "Type:").upper())

    first_place_row = html.find("div", class_="csstable-widget-row background-color-first-place")
    first_place_prize = first_place_row.find_next().find_next_sibling().text

    image_src = html.find("div", class_="infobox-image").find("img", src=True)["src"]
    logo_url = f"https://liquipedia.net{image_src}"

    return {"start_date": start_date, "end_date": end_date, "prize_pool": prize_pool, "location": location,
            "tier": tier, "type": type, "first_place_prize": first_place_prize, "logo_url": logo_url}

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


def get_team_logo_filepath(team_url: str, team_name: str) -> str | None:
    """
    Attempt to retrieve the logo from the HLTV team page, if not possible, attempt to retrieve the team logo from
    the liquipedia wiki. If the logo is retrieved, return the path to the file. If neither method works, return None.
    """
    html = requests.get(url=team_url).text
    soup = BeautifulSoup(html, "html.parser")

    # Attempt to retrieve the svg team logo from the HLTV team page.
    logo_url = soup.find("img", class_="teamlogo", src=True)["src"]
    logo_filename = f"{team_name.replace(' ', '_')}.png"
    Path("media/teams").mkdir(parents=True, exist_ok=True)

    if ".svg?" in logo_url:
        svg = requests.get(logo_url).text
        svg2png(bytestring=svg, write_to=f"media/teams/{logo_filename}")

        return logo_filename
    else:
        # If the logo is too small or could not be retrieved from HLTV, attempt to retrieve it from liquipedia.
        liquipedia_team_url = f"https://liquipedia.net/counterstrike/{team_name.replace(' ', '_')}"
        html = requests.get(url=liquipedia_team_url).text
        soup = BeautifulSoup(html, "html.parser")

        infobox = soup.find("div", class_="infobox-image")
        image_tag = infobox.find("img", src=True) if infobox else None

        if image_tag is not None:
            logo_url = f"https://liquipedia.net{image_tag['src']}"
            download_file_from_url(logo_url, f"teams/{logo_filename}")
            return logo_filename
        else:
            return None


def get_tournament_table_data(html: BeautifulSoup, row_text: str) -> str:
    """Return the data of the row with the given text in the tournament information table."""
    tag = html.find("div", class_="infobox-cell-2 infobox-description", text=row_text)
    return tag.find_next_sibling().text


def convert_letter_tier_to_number_tier(letter_tier: str) -> int:
    """Convert the given letter tier to the corresponding number tier."""
    conversion = {"s": 5, "s-tier": 5, "a": 4, "a-tier": 4, "b": 3, "b-tier": 3, "c": 2, "c-tier": 2, "d": 1}

    return conversion[letter_tier]


def convert_label_to_format(label: str) -> ScheduledMatch.Format:
    """Convert the given number to the corresponding match format."""
    if label == "bo1":
        return ScheduledMatch.Format.BEST_OF_1
    elif label == "bo3":
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
