import logging

from bs4 import BeautifulSoup
from django_celery_beat.models import PeriodicTask

from scrapers.models import Match, Tournament, Team


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
        raise NotImplementedError

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
