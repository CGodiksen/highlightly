import csv
import os
import re
import subprocess
import urllib.parse
from datetime import datetime, timedelta
from math import ceil
from pathlib import Path

import patoolib
import requests
from bs4 import BeautifulSoup, Tag
from cairosvg import svg2png
from demoparser import DemoParser
from serpapi import GoogleSearch

from scrapers.models import Match, Tournament, Team, Game, GameVod, GOTVDemo
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
            if match["team_1_name"] != "TBD" and match["team_2_name"] != "TBD":
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

            tournament = Tournament.objects.create(game=Game.COUNTER_STRIKE, name=match["tournament_name"],
                                                   url=tournament_url, start_date=data["start_date"],
                                                   end_date=data["end_date"], prize_pool_us_dollars=data["prize_pool"],
                                                   first_place_prize_us_dollars=data["first_place_prize"],
                                                   location=data["location"], tier=data["tier"], type=data["type"])

        return tournament

    @staticmethod
    def create_team(team_name, team_id) -> Team:
        team = Team.objects.filter(game=Game.COUNTER_STRIKE, name=team_name).first()
        if team is None:
            team_url = f"https://www.hltv.org/team/{team_id}/{team_name.replace(' ', '-').lower()}"

            # Extract the nationality and world ranking of the team.
            html = requests.get(url=team_url).text
            soup = BeautifulSoup(html, "html.parser")

            nationality = soup.find("div", class_="team-country text-ellipsis").text.strip()
            ranking = int(soup.find("b", text="World ranking").find_next_sibling().text[1:])

            # Retrieve the team logo if possible.
            logo_filename = get_team_logo_filename(team_url, team_name)

            team = Team.objects.create(game=Game.COUNTER_STRIKE, name=team_name, logo_filename=logo_filename,
                                       nationality=nationality, ranking=ranking, url=team_url)

        return team

    @staticmethod
    def create_scheduled_match(match: MatchData, tournament: Tournament, team_1: Team, team_2: Team) -> None:
        # Estimate the end datetime based on the start datetime and format.
        minimum_minutes = convert_format_to_minimum_time(match["format"])
        estimated_end_datetime = match["start_datetime"] + timedelta(minutes=minimum_minutes)

        # Automatically mark the scheduled match for highlight creation if it is tier 1 or higher.
        create_video = match["tier"] >= 1

        Match.objects.create(team_1=team_1, team_2=team_2, tournament=tournament, format=match["format"],
                             tier=match["tier"], url=match["url"], start_datetime=match["start_datetime"],
                             create_video=create_video, estimated_end_datetime=estimated_end_datetime)

    @staticmethod
    def is_match_finished(scheduled_match: Match) -> BeautifulSoup | None:
        html = requests.get(url="https://www.hltv.org/results").text
        soup = BeautifulSoup(html, "html.parser")

        # Check if the match url can be found on the results page.
        match_url_postfix = scheduled_match.url.removeprefix("https://www.hltv.org")

        if soup.find("a", class_="a-reset", href=match_url_postfix) is not None:
            # Check if the GOTV demo and vods can be found on the match page.
            match_soup = get_protected_page_html(scheduled_match.url, "match_page.txt")

            demo_found = match_soup.find("div", class_="flexbox", text="GOTV Demo sponsored by Bitskins") is not None
            vods_found = match_soup.findAll("img", class_="stream-flag flag")

            return html if demo_found and len(vods_found) > 0 else None

        return None

    @staticmethod
    def download_match_files(match: Match, html: BeautifulSoup) -> None:
        demos_folder_path = f"demos/{match.create_unique_folder_path()}"
        Path(f"media/{demos_folder_path}").mkdir(parents=True, exist_ok=True)

        vods_folder_path = f"vods/{match.create_unique_folder_path()}"
        Path(f"media/{vods_folder_path}").mkdir(parents=True, exist_ok=True)

        # Retrieve the tournament logo and tournament context of the match.
        extract_match_page_tournament_data(match, html)

        # Download the .rar GOTV demo file and unzip it to get the individual demo files.
        demo_url = f"https://www.hltv.org{html.find('a', class_='stream-box')['data-demo-link']}"

        download_file_from_url(demo_url, f"{demos_folder_path}/demos.rar")
        patoolib.extract_archive(f"media/{demos_folder_path}/demos.rar", outdir=f"media/{demos_folder_path}")

        # Delete the rar file after unzipping.
        Path(f"media/{demos_folder_path}/demos.rar").unlink(missing_ok=True)

        # For each demo, download the vod for the corresponding game from Twitch.
        vod_urls = html.findAll("img", class_="stream-flag flag")
        for game_count, demo_file in enumerate(os.listdir(f"media/{demos_folder_path}")):
            vod_url = vod_urls[game_count].parent.parent["data-stream-embed"]
            (video_id, start_time, end_time) = parse_twitch_vod_url(vod_url, f"media/{demos_folder_path}/{demo_file}")

            # Add 10 seconds to the start and end of the video to account for small timing errors.
            vod_start = start_time - timedelta(seconds=10)
            vod_end = end_time + timedelta(seconds=10)

            vod_filename = f"game_{game_count + 1}.mkv"
            vod_filepath = f"media/{vods_folder_path}/{vod_filename}"
            subprocess.run(f"twitch-dl download -q source -s {vod_start} -e {vod_end} -o {vod_filepath} {video_id}",
                           shell=True)

            # Persist the location of the files and other needed information about the vods to the database.
            game_map = vod_urls[game_count].next_sibling.text.split(" ")[-1].removesuffix(")")
            game_vod = GameVod.objects.create(match=match, game_count=game_count, map=game_map, url=vod_url,
                                              host=GameVod.Host.TWITCH, language="english", filename=vod_filename)

            GOTVDemo.objects.create(game_vod=game_vod, filename=demo_file)

    @staticmethod
    def extract_match_statistics(html: BeautifulSoup) -> None:
        # TODO: For both teams, find the statistics table.
        # TODO: Convert the HTML tables into csv.
        # TODO: Save the csv files and save the name of the file on the gave vod object.
        pass


# TODO: Change this function back when done with testing.
def get_protected_page_html(protected_url: str, test=None) -> BeautifulSoup:
    """Return the HTML for the given URL. This bypasses cloudflare protections."""
    if test:
        with open(f"../data/test/{test}", "r") as f:
            html = f.read()
    else:
        base_url = " https://api.scrapingant.com"
        safe_protected_url = urllib.parse.quote_plus(protected_url)
        url = f"{base_url}/v2/general?url={safe_protected_url}&x-api-key={os.environ['SCRAPING_API_KEY']}"

        html = requests.get(url=url).text

    return BeautifulSoup(html, "html.parser")


def extract_match_data(html: Tag, base_url: str) -> MatchData:
    """Given the HTML for a row in the upcoming matches table, extract the data for a match."""
    team_1_id = int(html["team1"])
    team_1_name = extract_team_name(html, 1)

    team_2_id = int(html["team2"])
    team_2_name = extract_team_name(html, 2)

    match_url_postfix = html.find("a", class_="match a-reset")["href"]
    match_url = f"{base_url}{match_url_postfix}"

    unix_timestamp = int(html.find("div", class_="matchTime")["data-unix"])
    start_datetime = datetime.utcfromtimestamp(unix_timestamp / 1000)
    match_format = convert_label_to_format(html.find("div", class_="matchMeta").text)

    tier = int(html["stars"])
    tournament_name: str = html.find("div", class_="matchEventName").text

    return {"url": match_url, "team_1_id": team_1_id, "team_1_name": team_1_name, "team_2_id": team_2_id,
            "team_2_name": team_2_name, "start_datetime": start_datetime, "tier": tier, "format": match_format,
            "tournament_name": tournament_name}


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

    return {"start_date": start_date, "end_date": end_date, "prize_pool": prize_pool, "location": location,
            "tier": tier, "type": type, "first_place_prize": first_place_prize}


def extract_match_page_tournament_data(match: Match, html: BeautifulSoup) -> None:
    """Extract the tournament logo and tournament context of the match from the match page HTML."""
    tournament_logo_url = html.find("img", class_="matchSidebarEventLogo", src=True)["srcset"].removesuffix(" 2x")

    Path("media/tournaments").mkdir(parents=True, exist_ok=True)
    logo_filename = f"{match.tournament.name.replace(' ', '_')}.png"
    download_file_from_url(tournament_logo_url, f"tournaments/{logo_filename}")

    match_info = html.find("div", class_="padding preformatted-text").text
    tournament_context = match_info.split("*")[1].strip()

    Match.objects.filter(id=match.id).update(tournament_context=tournament_context)
    Tournament.objects.filter(id=match.tournament.id).update(logo_filename=logo_filename)


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


def get_team_logo_filename(team_url: str, team_name: str) -> str | None:
    """Retrieve the SVG or PNG logo from the HLTV team page and return the name of the saved file."""
    html = requests.get(url=team_url).text
    soup = BeautifulSoup(html, "html.parser")

    # Attempt to retrieve the svg team logo from the HLTV team page.
    logo_img = soup.find("img", class_="teamlogo", src=True)
    logo_filename = f"{team_name.replace(' ', '_')}.png"
    Path("media/teams").mkdir(parents=True, exist_ok=True)

    if ".svg?" in logo_img["src"]:
        svg = requests.get(logo_img["src"]).text
        svg2png(bytestring=svg, write_to=f"media/teams/{logo_filename}")
    else:
        # If the logo is a PNG, find the largest version possible and download it.
        large_size_url = soup.find("img", class_="team-background-logo")["srcset"].removesuffix(" 2x")
        download_file_from_url(large_size_url, f"teams/{logo_filename}")

    return logo_filename


def get_tournament_table_data(html: BeautifulSoup, row_text: str) -> str:
    """Return the data of the row with the given text in the tournament information table."""
    tag = html.find("div", class_="infobox-cell-2 infobox-description", text=row_text)
    return tag.find_next_sibling().text


def convert_letter_tier_to_number_tier(letter_tier: str) -> int:
    """Convert the given letter tier to the corresponding number tier."""
    conversion = {"s": 5, "s-tier": 5, "a": 4, "a-tier": 4, "b": 3, "b-tier": 3, "c": 2, "c-tier": 2, "d": 1}

    return conversion[letter_tier]


def convert_label_to_format(label: str) -> Match.Format:
    """Convert the given number to the corresponding match format."""
    if label == "bo1":
        return Match.Format.BEST_OF_1
    elif label == "bo3":
        return Match.Format.BEST_OF_3
    else:
        return Match.Format.BEST_OF_5


def convert_format_to_minimum_time(match_format: Match.Format) -> int:
    """
    Return the minimum number of minutes required to complete a match with the given format. We assume each game takes
    at least 30 minutes and that there is at least 5 minutes of break between games.
    """
    if match_format == Match.Format.BEST_OF_1:
        return 1 * 30
    elif match_format == Match.Format.BEST_OF_3:
        return (2 * 30) + 5
    else:
        return (3 * 30) + 10


def parse_twitch_vod_url(twitch_vod_url: str, demo_filepath: str) -> (str, timedelta, timedelta):
    """Parse the url to retrieve the video ID and start time/end time for the game in the full Twitch video."""
    parser = DemoParser(demo_filepath)
    game_length_seconds = float(parser.parse_header()["playback_time"])

    split_url = twitch_vod_url.split("&")
    video_id = split_url[0].removeprefix("https://player.twitch.tv/?video=v")

    start_time = convert_twitch_timestamp_to_timedelta(split_url[2].removeprefix("t="))
    end_time = timedelta(seconds=ceil(game_length_seconds)) + start_time

    return video_id, start_time, end_time


def convert_twitch_timestamp_to_timedelta(timestamp: str) -> timedelta:
    """Convert the given Twitch video timestamp to a timedelta object."""
    hours = int(timestamp.split("h")[0]) if "h" in timestamp else 0
    minutes = int(re.sub("\D", "", timestamp.split("m")[0][-2:])) if "m" in timestamp else 0
    seconds = int(re.sub("\D", "", timestamp.split("s")[0][-2:])) if "s" in timestamp else 0

    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def save_html_table_to_csv(html_table: Tag, filepath: str) -> None:
    """Convert the given HTML table to CSV and save the CSV data to a file."""
    headers = [th.text.strip() for th in html_table.select("tr.header-row td")]

    with open(filepath, "w") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        rows = [[td.text.strip().split("\n")[0] for td in row.findAll("td")] for row in html_table.select("tr + tr")]
        writer.writerows(rows)
