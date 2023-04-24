import requests
from bs4 import BeautifulSoup
from django_celery_beat.models import PeriodicTask

from scrapers.models import Match, Tournament, Team
from scrapers.types import MatchData


class Scraper:
    @staticmethod
    def list_upcoming_matches() -> list[MatchData]:
        """Scrape for upcoming matches and return the list of found matches."""
        raise NotImplementedError

    @staticmethod
    def scheduled_match_already_exists(match: MatchData) -> bool:
        """Return True if a Match object already exists for the given match."""
        return Match.objects.filter(start_datetime=match["start_datetime"], team_1__name=match["team_1_name"],
                                    team_2__name=match["team_2_name"]).exists()

    @staticmethod
    def create_tournament(match: MatchData) -> Tournament:
        """
        Based on the information in the given match, create a Tournament object and return it. If an object for the
        tournament already exists, the existing object is returned.
        """
        raise NotImplementedError

    @staticmethod
    def create_team(team_name: str, team_id: int) -> Team:
        """
        Based on the information in the given match, create a Team object and return it. If an object for the team
        already exists, the existing object is returned.
        """
        raise NotImplementedError

    @staticmethod
    def create_scheduled_match(match: MatchData, tournament: Tournament, team_1: Team, team_2: Team) -> None:
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

        # For each remaining match in the list, create a Match object.
        for match in new_matches:
            tournament = self.create_tournament(match)
            team_1 = self.create_team(match["team_1_name"], match["team_1_id"])
            team_2 = self.create_team(match["team_2_name"], match["team_2_id"])

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

    # TODO: The videos application should have a signal on the FinishedMatch object to check when the highlights are done and should start the upload after.
    def scrape_finished_match(self, match: Match) -> None:
        """
        Check if the scheduled match is finished. If so, scrape all data required from the match page to create
        highlights, create a highlight video, and complete the video metadata.
        """
        html = self.is_match_finished(match)

        if html is not None:
            periodic_task = PeriodicTask.objects.get(name=f"Check if {match} is finished")
            periodic_task.delete()

            self.download_match_files(match, html)
            self.extract_match_statistics(html)

            match.finished = True
            match.save(update_fields=["finished"])
