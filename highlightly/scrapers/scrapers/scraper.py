import logging
import os
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from django_celery_beat.models import PeriodicTask
from serpapi import GoogleSearch

from scrapers.models import Match, Tournament, Team, Game
from scrapers.types import TournamentData


class Scraper:
    @staticmethod
    def list_upcoming_matches() -> list[dict]:
        """Scrape for upcoming matches and return the list of found matches."""
        raise NotImplementedError

    @staticmethod
    def scheduled_match_already_exists(match: dict) -> bool:
        """Return True if a Match object already exists for the given match."""
        return Match.objects.filter(start_datetime=match["start_datetime"], team_1__name=match["team_1"]["name"],
                                    team_2__name=match["team_2"]["name"]).exists()

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
                                                   location=data["location"], tier=data["tier"], type=data["type"])

        return tournament

    @staticmethod
    def create_team(team_data: dict) -> Team:
        """
        Based on the information in the given match, create a Team object and return it. If an object for the team
        already exists, the existing object is returned.
        """
        raise NotImplementedError

    @staticmethod
    def create_scheduled_match(match: dict, tournament: Tournament, team_1: Team, team_2: Team) -> None:
        """Based on the information in the given match, create a Match object."""
        raise NotImplementedError

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
            team_1 = self.create_team(match["team_1"])
            team_2 = self.create_team(match["team_2"])

            self.create_scheduled_match(match, tournament, team_1, team_2)

    @staticmethod
    def is_match_finished(scheduled_match: Match) -> BeautifulSoup | None:
        """Return the page HTML if the match is finished and ready for further processing. Otherwise, return None."""
        raise NotImplementedError

    @staticmethod
    def download_match_files(match:Match, html: BeautifulSoup) -> None:
        """
        Download all required files from the match page url such as vods, missing logos, and demo files. For each vod,
        a game vod object is created.
        """
        raise NotImplementedError

    @staticmethod
    def extract_match_statistics(match: Match, html: BeautifulSoup) -> None:
        """
        Extract and save per-game statistics for the entire match. Also determine the MVP based on the statistics
        and extract the players photo and advanced statistics if possible.
        """
        raise NotImplementedError

    def scrape_finished_match(self, match: Match) -> None:
        """
        Check if the scheduled match is finished. If so, scrape all data required from the match page to create
        highlights, create a highlight video, and complete the video metadata.
        """
        logging.info(f"Checking if {match} is finished and ready for post-match scraping.")
        html = self.is_match_finished(match)

        if html is not None:
            logging.info(f"{match} is ready for post-match scraping.")
            PeriodicTask.objects.filter(name=f"Scrape {match} if finished").delete()

            self.download_match_files(match, html)
            self.extract_match_statistics(match, html)

            logging.info(f"All data required for processing {match} has been scraped.")

            match.finished = True
            match.save(update_fields=["finished"])


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

    return result["organic_results"][0]["link"] if len(result["organic_results"]) > 0 else None


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
