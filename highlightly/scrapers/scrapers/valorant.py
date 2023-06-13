import csv
import logging
import os
import subprocess
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

from scrapers.models import Match, Game, Organization, GameVod, Player, Team
from scrapers.scrapers.scraper import Scraper, finish_vod_stream_download
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

    def check_match_status(self, match: Match):
        """Check the current match status and start the highlighting process if a game is finished."""
        html = requests.get(url=match.url).text
        soup = BeautifulSoup(html, "html.parser")

        # If it is the last game of the match, mark the match as finished and delete the related periodic task.
        if "final" in soup.find("div", class_="match-header-vs-note").text:
            logging.info(f"{match} is finished. Deleting the periodic task.")

            PeriodicTask.objects.filter(name=f"Check {match} status").delete()

            match.finished = True
            match.save()

        # Find the current number of finished games.
        score_spans = soup.find("div", class_="match-header-vs-score").findAll("span")
        game_counts = [int(span.text.strip()) for span in score_spans if span.text.strip().isdigit()]
        finished_game_count = sum(game_counts)

        # If a new game has started, create an object for the game.
        is_live = soup.find("span", class_="match-header-vs-note mod-live") is not None
        if is_live and not match.gamevod_set.filter(game_count=finished_game_count + 1).exists():
            logging.info(f"Game {finished_game_count + 1} for {match} has started. Creating object for game.")

            # Start downloading the livestream related to the game. This stream is only stopped when the game is finished.
            stream_url = get_twitch_stream_url(match, soup)
            logging.info(f"Connecting to stream from {stream_url} to download VOD.")

            vod_filename = f"game_{finished_game_count + 1}.mkv"
            vod_filepath = f"{match.create_unique_folder_path('vods')}/{vod_filename}"

            download_cmd = f"streamlink {stream_url} best -O | ffmpeg -re -i pipe:0 -filter:v scale=1920:-1 -c:a copy {vod_filepath}"
            process = subprocess.Popen(download_cmd, stdout=subprocess.PIPE, shell=True, preexec_fn=os.setsid)

            # Since we assume the game has just started, delay the task to check the match status.
            new_task_start_time = timezone.localtime(timezone.now()) + timedelta(minutes=30)
            PeriodicTask.objects.filter(name=f"Check {match} status").update(start_time=new_task_start_time)

            GameVod.objects.create(match=match, game_count=finished_game_count + 1, host=GameVod.Host.TWITCH,
                                   language="english", start_datetime=timezone.localtime(timezone.now()),
                                   process_id=process.pid, filename=vod_filename, url=stream_url)

        # Check if the most recently finished game has been marked as finished.
        if match.gamevod_set.filter(game_count=finished_game_count).exists():
            finished_game = match.gamevod_set.get(game_count=finished_game_count)
            if not finished_game.finished:
                logging.info(f"Game {finished_game_count} for {match} is finished. Starting highlighting process.")

                finish_vod_stream_download(finished_game)
                self.add_post_game_data(finished_game, soup)

                logging.info(f"Extracting game statistics for {finished_game}.")
                self.extract_game_statistics(finished_game, soup)

                finished_game.finished = True
                finished_game.save(update_fields=["finished"])

    @staticmethod
    def add_post_game_data(game_vod: GameVod, html: BeautifulSoup) -> None:
        """Update the game vod object with the post game data."""
        # Retrieve the tournament logo and tournament context of the match.
        extract_match_page_tournament_data(game_vod.match, html)

        # Update the game vod object with the post game data.
        game = html.findAll("div", class_="vm-stats-gamesnav-item", attrs={"data-disabled": "0"})[game_vod.game_count]
        game_stats = html.find("div", class_="vm-stats-game", attrs={"data-game-id": game["data-game-id"]})

        game_map = game_stats.find("div", class_="map").find("span").text.replace("PICK", "").strip()
        round_count = [int(score.text) for score in game_stats.findAll("div", class_="score")]

        # Persist the location of the files and other needed information about the vods to the database.
        game_vod.map = game_map
        game_vod.team_1_round_count = round_count[0]
        game_vod.team_2_round_count = round_count[1]
        game_vod.save()

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
    def get_mvp_url(table_group: BeautifulSoup) -> str:
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
    start_datetime = datetime.strptime(f"{date} {time}", "%a, %B %d, %Y %I:%M %p")

    # TODO: Find the actual format and tier.
    return {"game": Game.VALORANT, "team_1": team_1, "team_2": team_2, "start_datetime": start_datetime,
            "format": Match.Format.BEST_OF_3, "tier": 1, "url": match_url}


def extract_match_page_tournament_data(match: Match, html: BeautifulSoup) -> None:
    """Extract the tournament logo and tournament context of the match from the match page HTML."""
    Path("media/tournaments").mkdir(parents=True, exist_ok=True)
    logo_filename = f"{match.tournament.name.replace(' ', '_')}.png"

    # Only download the tournament logo if it does not already exist.
    if match.tournament.logo_filename is None:
        tournament_logo_img = html.find("a", class_="match-header-event", href=True).find("img")
        urllib.request.urlretrieve(f"https:{tournament_logo_img['src']}", f"media/tournaments/{logo_filename}")

        match.tournament.logo_filename = logo_filename
        match.tournament.save()

    tournament_context = html.find("div", class_="match-header-event-series").text.strip()
    match.tournament_context = " ".join(tournament_context.split())
    match.save()


def get_twitch_stream_url(match: Match, html: BeautifulSoup) -> dict:
    """Return the best Twitch stream URL related to the game."""
    stream_divs = html.findAll("div", class_="match-streams-btn")
    stream_url = stream_divs[0].find("a")["href"]

    valid_stream_languages = ["mod-un", "mod-eu", "mod-us", "mod-au"]

    # Only ban the main Valorant channel for non-international tournaments.
    if match.tournament.name in ["Champions Tour 2023: Masters Tokyo"]:
        banned_streams = []
    else:
        banned_streams = ["https://www.twitch.tv/valorant"]

    for stream_div in stream_divs:
        stream_flag = stream_div.find("i", class_="flag")
        stream_div_url = stream_div.find("a")["href"]

        # Only allow stream urls from english speaking streams and non-banned streams.
        if stream_flag["class"][1] in valid_stream_languages and stream_div_url not in banned_streams:
            return stream_div_url

    return stream_url
