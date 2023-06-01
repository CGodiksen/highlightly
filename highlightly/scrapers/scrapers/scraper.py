import logging
import os
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup, Tag
from serpapi import GoogleSearch

from scrapers.models import Match, Tournament, Team, Game, Organization, Player, GameVod
from scrapers.types import TournamentData, TeamData


class Scraper:
    @staticmethod
    def list_upcoming_matches() -> list[dict]:
        """Scrape for upcoming matches and return the list of found matches."""
        raise NotImplementedError

    @staticmethod
    def scheduled_match_already_exists(match: dict) -> bool:
        """Return True if a Match object already exists for the given match."""
        cleaned_team_1_name = match["team_1"]["name"].removeprefix("Team ").removesuffix(" Clan").strip()
        cleaned_team_2_name = match["team_2"]["name"].removeprefix("Team ").removesuffix(" Clan").strip()

        return Match.objects.filter(start_datetime=match["start_datetime"],
                                    team_1__organization__name__icontains=cleaned_team_1_name,
                                    team_2__organization__name__icontains=cleaned_team_2_name).exists()

    @staticmethod
    def create_tournament(match: dict) -> Tournament:
        """
        Based on the information in the given match, create a Tournament object and return it. If an object for the
        tournament already exists, the existing object is returned.
        """
        tournament = Tournament.objects.filter(game=match["game"], name=match["tournament_name"]).first()
        if tournament is None:
            logging.info(f"{match['tournament_name']} does not already exist. Creating new tournament.")

            tournament_url = get_liquipedia_tournament_url(match["tournament_name"], match["game"])
            html = requests.get(url=tournament_url).text
            soup = BeautifulSoup(html, "html.parser")

            # Extract the tournament data from the HTML.
            data = extract_tournament_data(soup)
            logging.info(f"Extracted data from {tournament_url} to create tournament for {match['tournament_name']}.")

            tournament = Tournament.objects.create(game=match["game"], name=match["tournament_name"],
                                                   url=tournament_url, start_date=data["start_date"],
                                                   end_date=data["end_date"], prize_pool_us_dollars=data["prize_pool"],
                                                   first_place_prize_us_dollars=data["first_place_prize"],
                                                   location=data["location"], tier=data["tier"], type=data["type"],
                                                   short_name=match.get("tournament_short_name", None))

        return tournament

    @staticmethod
    def extract_team_data(match_team_data: dict, organization: Organization) -> TeamData:
        """Parse through the match team data to extract the team data that can be used to create a team object."""
        raise NotImplementedError

    def create_team(self, match_team_data: dict, game: Game) -> Team:
        """
        Based on the information in the given match, create a Team object and return it. If an object for the team
        already exists, the existing object is returned.
        """
        team_name: str = match_team_data["name"]
        cleaned_team_name = team_name.removeprefix("Team ").removesuffix(" Clan").strip()
        team = Team.objects.filter(game=game, organization__name__icontains=cleaned_team_name).first()

        if team is None:
            logging.info(f"{team_name} does not already exist. Creating new team.")

            organization = Organization.objects.filter(name__icontains=cleaned_team_name).first()
            if organization is None:
                organization = Organization.objects.create(name=team_name)

            team_data = self.extract_team_data(match_team_data, organization)
            logging.info(f"Extracted data from {team_data['url']} to create team for {team_name}.")

            team = Team.objects.create(organization=organization, game=game, nationality=team_data["nationality"],
                                       ranking=team_data["ranking"], url=team_data["url"])

        return team

    @staticmethod
    def create_scheduled_match(match: dict, tournament: Tournament, team_1: Team, team_2: Team) -> None:
        """Based on the information in the given match, create a Match object."""
        # Estimate the end datetime based on the start datetime and format.
        minimum_minutes = convert_format_to_minimum_time(match["format"])
        estimated_end_datetime = match["start_datetime"] + timedelta(minutes=minimum_minutes)

        # Automatically mark the scheduled match for highlight creation if it is tier 1 or higher.
        create_video = match["tier"] >= 1

        logging.info(f"Creating scheduled match for {team_1.organization.name} VS. {team_2.organization.name}.")
        Match.objects.create(team_1=team_1, team_2=team_2, tournament=tournament, format=match["format"],
                             tier=match["tier"], url=match["url"], start_datetime=match["start_datetime"],
                             create_video=create_video, estimated_end_datetime=estimated_end_datetime,
                             stream_url=match.get("stream_url", None))

    def scrape_upcoming_matches(self) -> None:
        """
        Scrape for upcoming matches. For each new match that is found, a Match object is created. If the match
        already exists, the match is ignored.
        """
        # List the current upcoming matches in HLTV.
        matches = self.list_upcoming_matches()

        # Remove the matches from the given list of matches that already have a corresponding Match object.
        new_matches = [match for match in matches if not self.scheduled_match_already_exists(match)]
        logging.info(f"Found {len(matches)} upcoming matches and {len(new_matches)} new upcoming matches.")

        # For each remaining match in the list, create a Match object.
        for match in new_matches:
            tournament = self.create_tournament(match)
            team_1 = self.create_team(match["team_1"], match["game"])
            team_2 = self.create_team(match["team_2"], match["game"])

            self.create_scheduled_match(match, tournament, team_1, team_2)

    @staticmethod
    def is_match_finished(scheduled_match: Match) -> BeautifulSoup | None:
        """Return the page HTML if the match is finished and ready for further processing. Otherwise, return None."""
        raise NotImplementedError

    @staticmethod
    def download_match_files(match: Match, html: BeautifulSoup) -> None:
        """
        Download all required files from the match page url such as vods, missing logos, and demo files. For each vod,
        a game vod object is created.
        """
        raise NotImplementedError

    @staticmethod
    def get_statistics_table_groups(html: BeautifulSoup) -> list[BeautifulSoup]:
        """Return a statistics table group for each game in the match and for the total statistics."""
        raise NotImplementedError

    @staticmethod
    def get_statistics_tables(table_group: BeautifulSoup) -> list[BeautifulSoup]:
        """Return the tables in the given table group."""
        raise NotImplementedError

    @staticmethod
    def get_mvp_url(table_group: BeautifulSoup) -> list[BeautifulSoup]:
        """Find the MVP of the game and return the URL to the players page."""
        raise NotImplementedError

    @staticmethod
    def save_html_table_to_csv(html_table: Tag, filepath: str, team_name: str) -> None:
        """Convert the given HTML table to CSV and save the CSV data to a file."""
        raise NotImplementedError

    @staticmethod
    def extract_player_data(url: str) -> Player:
        """Retrieve information about the player from the given URL and create a player object."""
        raise NotImplementedError

    def extract_game_statistics(self, game: GameVod, html: BeautifulSoup) -> None:
        """
        Extract and save per-game statistics for the game. Also determine the MVP based on the statistics
        and extract the players photo and advanced statistics if possible.
        """
        statistics_folder_path = game.match.create_unique_folder_path("statistics")
        table_group = self.get_statistics_table_groups(html)[game.game_count]

        # Convert the HTML tables into CSV and save the filename on the game object.
        html_tables = self.get_statistics_tables(table_group)

        for (html_table, team) in zip(html_tables, [game.match.team_1, game.match.team_2]):
            team_name = team.organization.name.lower().replace(' ', '_')
            filename = f"map_{game.game_count}_{team_name}.csv"

            self.save_html_table_to_csv(html_table, f"{statistics_folder_path}/{filename}", team.organization.name)

            field_to_update = "team_1_statistics_filename" if game.match.team_1 == team else "team_2_statistics_filename"
            setattr(game, field_to_update, filename)
            game.save()

        # Find the MVP of the game and, if necessary, extract information about the player.
        player_url = self.get_mvp_url(table_group)

        if not Player.objects.filter(url=player_url).exists():
            mvp = self.extract_player_data(player_url)
        else:
            mvp = Player.objects.get(url=player_url)

        if mvp:
            game.mvp = mvp
            game.save()

    def scrape_finished_match(self, match: Match) -> None:
        """
        Check if the scheduled match is finished. If so, scrape all data required from the match page to create
        highlights, create a highlight video, and complete the video metadata.
        """
        logging.info(f"Checking if {match} is finished and ready for post-match scraping.")
        html = self.is_match_finished(match)

        if html is not None:
            logging.info(f"{match} is ready for post-match scraping.")
            self.download_match_files(match, html)


def get_liquipedia_tournament_url(tournament_name: str, game: Game) -> str | None:
    """
    Attempt to retrieve the url for the tournaments liquipedia wiki page. Since the liquipedia wiki search is faulty,
    use Google Search to find the corresponding liquipedia page.
    """
    # Since the liquipedia wiki search is faulty, use Google Search to find the corresponding liquipedia page.
    search = GoogleSearch({
        "engine": "google",
        "api_key": os.environ["SERP_API_KEY"],
        "q": f"{tournament_name} site:https://liquipedia.net/{game.replace('_', '').lower()}",
        "as_qdr": "w2"
    })
    result = search.get_dict()

    tournament_url: str | None = result["organic_results"][0]["link"] if len(result["organic_results"]) > 0 else None

    # Remove potential end parts of the URL that directs to a subpage of the main tournament page.
    if tournament_url is not None:
        suffixes_to_remove = ["Regular_Season", "Showmatch", "Statistics", "Additional_Content", "Group_Stage",
                              "Play-In_Stage", "Bracket_Stage", "Last_Chance_Qualifier", "Main_Stage",
                              "Contenders_Stage", "Qualifier/Europe", "Qualifier/Nordic"]

        for suffix in suffixes_to_remove:
            tournament_url = tournament_url.removesuffix(f"/{suffix}")

    return tournament_url


def extract_tournament_data(html: BeautifulSoup) -> TournamentData:
    """Given the HTML for the tournaments liquipedia wiki page, extract the data for the tournament."""
    start_date = datetime.strptime(get_tournament_table_data(html, "Start Date:"), "%Y-%m-%d").date()

    try:
        end_date = datetime.strptime(get_tournament_table_data(html, "End Date:"), "%Y-%m-%d").date()
    except ValueError:
        end_date = None

    prize_pool = get_tournament_table_data(html, "Prize Pool:").split("\xa0")[0]
    location = get_tournament_table_data(html, "Location:").strip()
    tier = convert_letter_tier_to_number_tier(get_tournament_table_data(html, "Liquipedia Tier:").lower().strip())
    type = Tournament.Type(get_tournament_table_data(html, "Type:").upper())

    first_place_row = html.find("div", class_="csstable-widget-row background-color-first-place")
    first_place_prize = first_place_row.find_next().find_next_sibling().text

    return {"start_date": start_date, "end_date": end_date, "prize_pool": prize_pool, "location": location,
            "tier": tier, "type": type, "first_place_prize": first_place_prize}


def get_tournament_table_data(html: BeautifulSoup, row_text: str) -> str:
    """Return the data of the row with the given text in the tournament information table."""
    tag = html.find("div", class_="infobox-cell-2 infobox-description", text=row_text)
    return tag.find_next_sibling().text if tag else ""


def convert_letter_tier_to_number_tier(letter_tier: str) -> int:
    """Convert the given letter tier to the corresponding number tier."""
    if "qualifier" in letter_tier:
        letter_tier = letter_tier[letter_tier.find("(") + 1:letter_tier.find(")")]

    conversion = {"s": 5, "s-tier": 5, "a": 4, "a-tier": 4, "b": 3, "b-tier": 3, "c": 2, "c-tier": 2, "d": 1}

    return conversion[letter_tier]


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
