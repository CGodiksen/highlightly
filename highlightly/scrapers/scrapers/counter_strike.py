import csv
import logging
import os
import re
import subprocess
import urllib.parse
from datetime import datetime, timedelta

import pytz
from django.utils import timezone
from math import ceil
from pathlib import Path

import patoolib
import requests
from bs4 import BeautifulSoup, Tag
from cairosvg import svg2png
from demoparser import DemoParser

from scrapers.models import Match, Team, Game, GameVod, GOTVDemo, Player, Organization
from scrapers.scrapers.scraper import Scraper
from scrapers.types import CounterStrikeMatchData, TeamData
from util.file_util import download_file_from_url


class CounterStrikeScraper(Scraper):
    """Webscraper that scrapes hltv.org for upcoming Counter-Strike matches."""

    @staticmethod
    def list_upcoming_matches() -> list[CounterStrikeMatchData]:
        logging.info("Scraping upcoming Counter-Strike matches from hltv.org.")

        upcoming_matches: list[CounterStrikeMatchData] = []

        base_url = "https://www.hltv.org"
        soup = get_protected_page_html(f"{base_url}/matches")

        # Find the table with matches from today.
        upcoming_matches_tables = soup.find_all("div", class_="upcomingMatchesSection")
        rows: list[Tag] = upcoming_matches_tables[0].find_all("div", class_="upcomingMatch")
        rows = [row for row in rows if row["stars"] != "0"]
        logging.info(f"Found {len(rows)} potential upcoming matches.")

        # For each row in the table, extract the teams, tournament, and match.
        for row in rows:
            match = extract_match_data(row, base_url)

            # Ignore the match if it currently still contains a "TBD" team.
            if match is not None and match["team_1"]["name"] != "TBD" and match["team_2"]["name"] != "TBD":
                logging.info(f"Extracted initial data for {match['team_1']['name']} VS. {match['team_2']['name']}.")
                match["game"] = Game.COUNTER_STRIKE
                upcoming_matches.append(match)

        return upcoming_matches

    @staticmethod
    def extract_team_data(match_team_data: dict, organization: Organization) -> TeamData:
        """Parse through the match team data to extract the team data that can be used to create a team object."""
        team_name = match_team_data["name"]
        team_url = f"https://www.hltv.org/team/{match_team_data['id']}/{team_name.replace(' ', '-').lower()}"

        # Extract the nationality and world ranking of the team.
        html = requests.get(url=team_url).text
        soup = BeautifulSoup(html, "html.parser")

        nationality = soup.find("div", class_="team-country text-ellipsis").text.strip()
        ranking = soup.find("b", text="World ranking").find_next_sibling().text[1:]
        ranking = int(ranking) if ranking.isdigit() else None

        # Retrieve the team logo if necessary.
        if organization.logo_filename is None:
            organization.logo_filename = get_team_logo_filename(soup, team_name)
            organization.save()

        return {"url": team_url, "nationality": nationality, "ranking": ranking}

    # TODO: Use https://www.hltv.org/results?content=demo&content=vod to check instead of checking the match page.
    @staticmethod
    def is_match_finished(scheduled_match: Match) -> BeautifulSoup | None:
        html = requests.get(url="https://www.hltv.org/results").text
        soup = BeautifulSoup(html, "html.parser")

        # Check if the match url can be found on the results page.
        match_url_postfix = scheduled_match.url.removeprefix("https://www.hltv.org")

        if soup.find("a", class_="a-reset", href=match_url_postfix) is not None:
            logging.info(f"{scheduled_match} is finished. Checking if GOTV demo and VODs are ready to be downloaded.")

            # Check if the GOTV demo and vods can be found on the match page.
            match_soup = get_protected_page_html(scheduled_match.url)

            demo_found = match_soup.find("div", class_="flexbox", text="GOTV Demo sponsored by Bitskins") is not None
            vods_found = match_soup.findAll("img", class_="stream-flag flag")

            logging.info(f"Found GOTV demo for {scheduled_match}.") if demo_found else logging.info(
                f"Could not find GOTV demo for {scheduled_match}.")
            logging.info(f"Found {len(vods_found)} VODs for {scheduled_match}.")

            return match_soup if demo_found and len(vods_found) > 0 else None

        return None

    def download_match_files(self, match: Match, html: BeautifulSoup) -> None:
        demos_folder_path = match.create_unique_folder_path("demos")
        vods_folder_path = match.create_unique_folder_path("vods")

        # Retrieve the tournament logo and tournament context of the match.
        extract_match_page_tournament_data(match, html)

        # Download the .rar GOTV demo file and unzip it to get the individual demo files.
        demo_url = f"https://www.hltv.org{html.find('a', class_='stream-box')['data-demo-link']}"

        download_file_from_url(demo_url, f"{demos_folder_path}/demos.rar")
        patoolib.extract_archive(f"{demos_folder_path}/demos.rar", outdir=demos_folder_path)

        # Delete the rar file after unzipping.
        Path(f"{demos_folder_path}/demos.rar").unlink(missing_ok=True)
        logging.info(f"Deleted {demos_folder_path}/demos.rar after unzipping.")

        # For each demo, download the vod for the corresponding game from Twitch.
        vod_urls = html.findAll("img", class_="stream-flag flag")
        results = html.findAll("div", class_="mapholder")

        for game_count, demo_file in enumerate(os.listdir(demos_folder_path)):
            vod_url = vod_urls[game_count].parent.parent["data-stream-embed"]
            logging.info(f"Downloading VOD for game {game_count + 1} of {match} from {vod_url}.")
            (video_id, start_time, end_time) = parse_twitch_vod_url(vod_url, f"{demos_folder_path}/{demo_file}")

            # Add 15 seconds to the start and end of the video to account for small timing errors.
            vod_start = start_time - timedelta(seconds=15)
            vod_end = end_time + timedelta(seconds=15)

            vod_filename = f"game_{game_count + 1}.mkv"
            vod_filepath = f"{vods_folder_path}/{vod_filename}"

            download_cmd = f"twitch-dl download -q source -s {vod_start} -e {vod_end} -o {vod_filepath} {video_id}"
            subprocess.run(download_cmd, shell=True)

            map = results[game_count].find("div", class_="mapname").text
            round_count = [int(score.text) for score in results[game_count].findAll("div", class_="results-team-score")]

            # Persist the location of the files and other needed information about the vods to the database.
            game_vod = GameVod.objects.create(match=match, game_count=game_count + 1, map=map, url=vod_url,
                                              host=GameVod.Host.TWITCH, language="english", filename=vod_filename,
                                              team_1_round_count=round_count[0], team_2_round_count=round_count[1],
                                              start_datetime=timezone.localtime(timezone.now()))

            GOTVDemo.objects.create(game_vod=game_vod, filename=demo_file)

            if game_count + 1 == len(os.listdir(demos_folder_path)):
                match.finished = True
                match.save()

            logging.info(f"Extracting game statistics for {game_vod}.")
            self.extract_game_statistics(game_vod, html)

            game_vod.finished = True
            game_vod.save(update_fields=["finished"])

    @staticmethod
    def get_statistics_table_groups(html: BeautifulSoup) -> list[BeautifulSoup]:
        """Return a statistics table group for each game in the match and for the total statistics."""
        return html.findAll("div", class_="stats-content")

    @staticmethod
    def get_statistics_tables(table_group: BeautifulSoup) -> list[BeautifulSoup]:
        """Return the tables in the given table group."""
        return table_group.findAll("table", class_="table totalstats")

    @staticmethod
    def get_mvp_url(table_group: BeautifulSoup) -> list[BeautifulSoup]:
        """Find the MVP of the game and return the URL to the players page."""
        player_rows = [row for row in table_group.select(".totalstats tr") if "header-row" not in row["class"]]
        mvp_row = max(player_rows, key=lambda row: float(row.find("td", class_="rating").text))
        return f"https://www.hltv.org{mvp_row.find('a')['href']}"

    @staticmethod
    def save_html_table_to_csv(html_table: Tag, filepath: str, _team_name: str) -> None:
        """Convert the given HTML table to CSV and save the CSV data to a file."""
        headers = [th.text.strip() for th in html_table.select("tr.header-row td")]

        with open(filepath, "w") as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            rows = [[td.text.strip().split("\n")[0] for td in row.findAll("td")] for row in
                    html_table.select("tr + tr")]
            writer.writerows(rows)

    @staticmethod
    def extract_player_data(url: str) -> Player:
        """Retrieve information about the player from the given URL and create a player object."""
        logging.info(f"Player in {url} does not already exist. Creating new player.")

        html = requests.get(url=url).text
        soup = BeautifulSoup(html, "html.parser")

        nationality = soup.find("img", class_="flag", itemprop="nationality")["title"]
        tag = soup.find("h1", class_="playerNickname", itemprop="alternateName").text.strip()
        name = soup.find("div", class_="playerRealname", itemprop="name").text.strip()

        team_url = soup.find("div", class_="playerInfoRow playerTeam").find("a", href=True)["href"]
        team = Team.objects.get(url=f"https://www.hltv.org{team_url}")

        profile_picture_url = soup.find("img", class_="bodyshot-img", src=True)["src"]
        profile_picture_filename = f"{team.organization.name.replace(' ', '-').lower()}-{tag.replace(' ', '-').lower()}.png"
        download_file_from_url(profile_picture_url, f"media/players/{profile_picture_filename}")

        return Player.objects.create(nationality=nationality, tag=tag, name=name, url=url, team=team,
                                     profile_picture_filename=profile_picture_filename)


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


def extract_match_data(html: Tag, base_url: str) -> CounterStrikeMatchData:
    """Given the HTML for a row in the upcoming matches table, extract the data for a match."""
    team_1_id = html.get("team1")
    team_2_id = html.get("team2")

    # If one of the teams is still TDB, return None and do not schedule the match.
    if team_1_id is None or team_2_id is None:
        return None

    team_1_name = extract_team_name(html, 1)
    team_2_name = extract_team_name(html, 2)

    match_url_postfix = html.find("a", class_="match a-reset")["href"]
    match_url = f"{base_url}{match_url_postfix}"

    unix_timestamp = int(html.find("div", class_="matchTime")["data-unix"])

    start_datetime = datetime.utcfromtimestamp(unix_timestamp / 1000).astimezone(pytz.timezone("Europe/Copenhagen"))
    match_format = convert_label_to_format(html.find("div", class_="matchMeta").text)

    tier = int(html["stars"])
    tournament_name: str = html.find("div", class_="matchEventName").text

    team_1_data = {"id": int(team_1_id), "name": team_1_name}
    team_2_data = {"id": int(team_2_id), "name": team_2_name}
    return {"url": match_url, "team_1": team_1_data, "team_2": team_2_data, "start_datetime": start_datetime,
            "tier": tier, "format": match_format, "tournament_name": tournament_name}


def extract_team_name(html: Tag, team_number: int) -> str:
    """Return the formatted name of either team 1 or team 2."""
    team_div = html.find("div", class_=f"matchTeam team{team_number}")
    team_name = team_div.text if team_div.find("div", class_="matchTeamLogoContainer") is not None else "TBD"

    return team_name.replace("\n", "")


def extract_match_page_tournament_data(match: Match, html: BeautifulSoup) -> None:
    """Extract the tournament logo and tournament context of the match from the match page HTML."""
    Path("media/tournaments").mkdir(parents=True, exist_ok=True)
    logo_filename = f"{match.tournament.name.replace(' ', '_')}.png"

    # Only download the tournament logo if it does not already exist.
    if match.tournament.logo_filename is None:
        tournament_logo_img = html.find("img", class_="matchSidebarEventLogo", src=True)

        if ".svg?" in tournament_logo_img["src"]:
            svg = requests.get(tournament_logo_img["src"]).text
            svg2png(bytestring=svg, write_to=f"media/tournaments/{logo_filename}")
        else:
            tournament_logo_url = tournament_logo_img["srcset"].removesuffix(" 2x")
            download_file_from_url(tournament_logo_url, f"media/tournaments/{logo_filename}")

        match.tournament.logo_filename = logo_filename
        match.tournament.save()

    match_info = html.find("div", class_="padding preformatted-text").text
    tournament_context = match_info.split("*")[1].strip()

    match.tournament_context = tournament_context
    match.save()


def get_team_logo_filename(team_soup: BeautifulSoup, team_name: str) -> str | None:
    """Retrieve the SVG or PNG logo from the HLTV team page and return the name of the saved file."""
    # Attempt to retrieve the svg team logo from the HLTV team page.
    logo_img = team_soup.find("img", class_="teamlogo", src=True)
    logo_filename = f"{team_name.replace(' ', '_')}.png"
    Path("media/teams").mkdir(parents=True, exist_ok=True)

    if ".svg" in logo_img["src"]:
        try:
            src = f"https://www.hltv.org{logo_img['src']}" if "placeholder.svg" in logo_img["src"] else logo_img["src"]
            svg = requests.get(src).text
            svg2png(bytestring=svg, write_to=f"media/teams/{logo_filename}")
        except Exception as e:
            print(f"Error when trying to convert SVG to PNG: {e}")
            return "default.png"
    else:
        # If the logo is a PNG, find the largest version possible and download it.
        large_size_url = team_soup.find("img", class_="team-background-logo")["srcset"].removesuffix(" 2x")
        download_file_from_url(large_size_url, f"media/teams/{logo_filename}")

    return logo_filename


def convert_label_to_format(label: str) -> Match.Format:
    """Convert the given number to the corresponding match format."""
    if label == "bo1":
        return Match.Format.BEST_OF_1
    elif label == "bo3":
        return Match.Format.BEST_OF_3
    else:
        return Match.Format.BEST_OF_5


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
