import requests
from bs4 import BeautifulSoup
from django_celery_beat.models import PeriodicTask

from scrapers.models import ScheduledMatch, Tournament, Team
from scrapers.types import MatchData


class Scraper:
    @staticmethod
    def list_upcoming_matches() -> list[MatchData]:
        """Scrape for upcoming matches and return the list of found matches."""
        raise NotImplementedError

    @staticmethod
    def scheduled_match_already_exists(match: MatchData) -> bool:
        """Return True if a ScheduledMatch object already exists for the given match."""
        return ScheduledMatch.objects.filter(start_datetime=match["start_datetime"], team_1__name=match["team_1_name"],
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
        """Based on the information in the given match, create a ScheduledMatch object."""
        raise NotImplementedError

    def scrape_upcoming_matches(self) -> None:
        """
        Scrape for upcoming matches. For each new match that is found, a ScheduledMatch object is created. If the match
        already exists, the match is ignored.
        """
        # List the current upcoming matches in HLTV.
        matches = self.list_upcoming_matches()

        # Remove the matches from the given list of matches that already have a corresponding ScheduledMatch object.
        new_matches = [match for match in matches if not self.scheduled_match_already_exists(match)]

        # For each remaining match in the list, create a ScheduledMatch object.
        for match in new_matches:
            tournament = self.create_tournament(match)
            team_1 = self.create_team(match["team_1_name"], match["team_1_id"])
            team_2 = self.create_team(match["team_2_name"], match["team_2_id"])

            self.create_scheduled_match(match, tournament, team_1, team_2)

    @staticmethod
    def is_match_finished(scheduled_match: ScheduledMatch) -> BeautifulSoup | None:
        """Return the page HTML if the match is finished and ready for further processing. Otherwise, return None."""
        raise NotImplementedError

    # TODO: Add extra conditions that check for the GOTV demo and vods before actually marking the match as done.
    # TODO: The information should be saved on a FinishedMatch object.
    # TODO: The videos application should have a signal on the FinishedMatch object that adds end game metadata when the object is created.
    # TODO: The highlighters application should have a signal on the FinishedMatch object that created highlighters when the object is created.
    # TODO: The videos application should have a signal on the FinishedMatch object to check when the highlights are done and should start the upload after.
    def scrape_finished_match(self, scheduled_match: ScheduledMatch) -> None:
        """
        Check if the scheduled match is finished. If so, scrape all data required from the match page to create
        highlights, create a highlight video, and complete the video metadata.
        """
        html = self.is_match_finished(scheduled_match)

        if html is not None:
            periodic_task = PeriodicTask.objects.get(name=f"Check if {scheduled_match} is finished")
            periodic_task.delete()

            scheduled_match.finished = True
            scheduled_match.save()

            # TODO: Download the vods of the games.
            # TODO: Download extra information required for highlighting such as GOTV demo.
            # TODO: Extract extra information required for metadata such as tournament logo and context.
            # TODO: Extract game and player statistics.
