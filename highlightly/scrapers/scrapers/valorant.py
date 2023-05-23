import csv
import json
import logging
import subprocess
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import pytz
import requests
from bs4 import BeautifulSoup, Tag

from scrapers.models import Match, Game, Organization, GameVod, Player, Team
from scrapers.scrapers.scraper import Scraper
from scrapers.types import TeamData


class ValorantScraper(Scraper):
    """Webscraper that scrapes vlr.gg for upcoming Valorant matches."""

    included_tournaments = ["Champions Tour 2023: Americas League", "Champions Tour 2023: EMEA League",
                            "Champions Tour 2023: Pacific League", "Champions Tour 2023: Masters Tokyo",
                            "Challengers League: North America"]

    def list_upcoming_matches(self) -> list[dict]:
        """Scrape vlr.gg for upcoming Valorant matches."""
        upcoming_matches = []
        html = requests.get(url="https://www.vlr.gg/matches").text
        soup = BeautifulSoup(html, "html.parser")

        # Find all match rows.
        match_rows = soup.findAll("a", class_="match-item")

        # For each match, extract the data necessary to create a tournament, teams, and match objects.
        for match_row in match_rows:
            tournament_name = match_row.find("div", class_="match-item-event").text.split("\n")[-1].strip()
            team_names = [team.text.strip() for team in match_row.findAll("div", class_="match-item-vs-team-name")]
            time = match_row.find("div", class_="match-item-time").text.strip()

            is_showmatch = "showmatch" in match_row.find("div", class_="match-item-event-series").text.lower()

            # Only add the match if is from an included tournament, both teams are determined, the time is determined, and it's not a showmatch.
            if tournament_name in self.included_tournaments and "TBD" not in team_names and time != "TBD" and not is_showmatch:
                match_data = extract_match_data(team_names, time, match_row)
                match_data["tournament_name"] = tournament_name

                upcoming_matches.append(match_data)

        return upcoming_matches

    @staticmethod
    def extract_team_data(match_team_data: dict, organization: Organization) -> TeamData:
        """Parse through the match team data to extract the team data that can be used to create a team object."""
        team_name = match_team_data["name"]

        # Find the URL of the team page.
        html = requests.get(url=match_team_data["match_url"]).text
        match_soup = BeautifulSoup(html, "html.parser")
        team_anchor = next(tag for tag in match_soup.findAll("a", class_="match-header-link") if team_name in tag.text)
        team_url = f"https://www.vlr.gg{team_anchor['href']}"

        # Find the nationality and ranking of the team from the team page.
        html = requests.get(url=team_url).text
        team_soup = BeautifulSoup(html, "html.parser")

        nationality = team_soup.find("div", class_="team-header-country").text.strip()
        ranking = int(team_soup.find("div", class_="rank-num mod-").text.strip())

        # Download the team logo and get the filename.
        team_logo_img = team_soup.find("div", class_="team-header-logo").find("img")
        team_logo_url = f"https:{team_logo_img['src']}"

        if organization.logo_filename is None:
            logo_filename = f"{team_name.replace(' ', '_')}.png"
            Path("media/teams").mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(team_logo_url, f"media/teams/{logo_filename}")

            organization.logo_filename = logo_filename
            organization.save()

        return {"url": team_url, "nationality": nationality, "ranking": ranking}

    @staticmethod
    def is_match_finished(scheduled_match: Match) -> BeautifulSoup | None:
        """Return the page HTML if the match is finished and ready for further processing. Otherwise, return None."""
        html = requests.get(url=scheduled_match.url).text
        soup = BeautifulSoup(html, "html.parser")

        status = soup.find("div", class_="match-header-vs-note").text.strip()

        return soup if status == "final" else None

    @staticmethod
    def download_match_files(match: Match, html: BeautifulSoup) -> None:
        """Download a VOD for each game in the match."""
        # Find the best stream url for the match.
        stream_divs = html.findAll("div", class_="match-streams-btn")
        stream_url = stream_divs[0].find("a")["href"]

        valid_stream_languages = ["mod-un", "mod-eu", "mod-us", "mod-au"]
        banned_streams = ["https://www.twitch.tv/valorant"]

        for stream_div in stream_divs:
            stream_flag = stream_div.find("i", class_="flag")
            stream_div_url = stream_div.find("a")["href"]

            # Only allow stream urls from english speaking streams and non-banned streams.
            if stream_flag["class"][1] in valid_stream_languages and stream_div_url not in banned_streams:
                stream_url = stream_div_url
                break

        # Find the latest video from the stream which should be the video with the VOD for each game.
        list_videos_cmd = f"twitch-dl videos -j {stream_url.split('/')[-1]}"
        result = subprocess.run(list_videos_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        video = json.loads(result.stdout.decode())["videos"][0]

        # Find the start time of the game in the full VOD.
        tz = pytz.timezone("Europe/Copenhagen")
        vod_started_at = datetime.strptime(video["publishedAt"], "%Y-%m-%dT%H:%M:%SZ").astimezone(tz)
        vod_match_start_offset = match.start_datetime.replace(tzinfo=None) - vod_started_at.replace(tzinfo=None)

        # Download the entire Twitch video from the start offset to now.
        logging.info(f"Downloading VOD for all games of {match} from {video['id']}.")

        vod_start = vod_match_start_offset - timedelta(minutes=5)
        vod_end = datetime.now(tz=tz).replace(tzinfo=None) - vod_started_at.replace(tzinfo=None)

        vods_folder_path = match.create_unique_folder_path("vods")
        vod_filepath = f"{vods_folder_path}/games.mkv"
        download_cmd = f"twitch-dl download -q source -s {vod_start} -e {vod_end} -o {vod_filepath} {video['id']}"
        subprocess.run(download_cmd, shell=True)

        # For each game, create a game vod object.
        games = html.findAll("div", class_="vm-stats-gamesnav-item", attrs={"data-disabled": "0"})[1:]
        for game_count, game in enumerate(games):
            game_stats = html.find("div", class_="vm-stats-game", attrs={"data-game-id": game["data-game-id"]})

            vod_url = f"https://www.twitch.tv/videos/{video['id']}"
            map = game_stats.find("div", class_="map").find("span").text.replace("PICK", "").strip()
            round_count = [int(score.text) for score in game_stats.findAll("div", class_="score")]

            # Persist the location of the files and other needed information about the vods to the database.
            GameVod.objects.create(match=match, game_count=game_count + 1, map=map, url=vod_url,
                                   host=GameVod.Host.TWITCH, language="english", filename="games.mkv",
                                   team_1_round_count=round_count[0], team_2_round_count=round_count[1])

    @staticmethod
    def get_statistics_table_groups(html: BeautifulSoup) -> list[BeautifulSoup]:
        """Return a statistics table group for each game in the match and for the total statistics."""
        stat_table_buttons = html.findAll("div", class_="vm-stats-gamesnav-item", attrs={"data-disabled": "0"})

        return [html.find("div", class_="vm-stats-game", attrs={"data-game-id": stat_table_button["data-game-id"]})
                for stat_table_button in stat_table_buttons]

    @staticmethod
    def get_statistics_tables(table_group: BeautifulSoup) -> list[BeautifulSoup]:
        """Return the tables in the given table group."""
        return table_group.findAll("table", class_="wf-table-inset")

    @staticmethod
    def get_mvp_url(table_group: BeautifulSoup) -> list[BeautifulSoup]:
        """Find the MVP of the game and return the URL to the players page."""
        player_rows = table_group.select("tbody tr")
        mvp_row = max(player_rows, key=lambda row: float(row.findAll("td")[2].find("span", class_="mod-both").text))
        return f"https://www.vlr.gg{mvp_row.find('a')['href']}"

    @staticmethod
    def save_html_table_to_csv(html_table: Tag, filepath: str, team_name: str) -> None:
        """Convert the given HTML table to CSV and save the CSV data to a file."""
        headers = [th.text.strip() for th in html_table.select("thead th")]
        headers[0] = team_name
        del headers[1]

        with open(filepath, "w") as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            rows = [[td.text.strip().split("\n")[0]
                     if td.text.strip().split("\n")[0] != "/" else td.text.strip().split("\n")[2]
                     for td in row.findAll("td")] for row in html_table.select("tbody tr")]

            for row in rows:
                row[0] = row[0].strip()
                del row[1]

            writer.writerows(rows)

    @staticmethod
    def extract_player_data(url: str) -> Player:
        """Retrieve information about the player from the given URL and create a player object."""
        logging.info(f"Player in {url} does not already exist. Creating new player.")

        html = requests.get(url=url).text
        soup = BeautifulSoup(html, "html.parser")

        nationality = soup.find("i", class_="flag").parent.text.strip()
        tag = soup.find("h1", class_="wf-title").text.strip()
        name = soup.find("h2", class_="player-real-name").text.strip()

        current_team = soup.find("h2", text=lambda x: "Current Teams" in x).find_next_sibling()
        team_url = current_team.find("a", href=True)["href"]
        team = Team.objects.get(url=f"https://www.vlr.gg{team_url}")

        profile_picture_url = soup.find("div", class_="wf-avatar mod-player").find("img")["src"]
        profile_picture_filename = f"{team.organization.name.replace(' ', '-').lower()}-{tag.replace(' ', '-').lower()}.png"
        full_url = f"https://www.vlr.gg{profile_picture_url}" if "base/ph/sil.png" in profile_picture_url else f"https:{profile_picture_url}"
        urllib.request.urlretrieve(full_url, f"media/players/{profile_picture_filename}")

        return Player.objects.create(nationality=nationality, tag=tag, name=name, url=url, team=team,
                                     profile_picture_filename=profile_picture_filename)


def extract_match_data(team_names: list[str], time: str, match_row: Tag) -> dict:
    """Extract the match data from the tag."""
    match_url = f"https://www.vlr.gg{match_row['href']}"

    team_1 = {"name": team_names[0], "match_url": match_url}
    team_2 = {"name": team_names[1], "match_url": match_url}

    date = match_row.parent.find_previous_sibling().text.strip()
    date = date.replace("\n", "").replace("\t", "").replace("Today", "").strip()
    start_datetime = datetime.strptime(f"{date} {time}", "%a, %b %d, %Y %I:%M %p")

    # TODO: Find the actual format and tier.
    return {"game": Game.VALORANT, "team_1": team_1, "team_2": team_2, "start_datetime": start_datetime,
            "format": Match.Format.BEST_OF_3, "tier": 1, "url": match_url}
