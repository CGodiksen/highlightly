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
        return ScheduledMatch.objects.filter(start_datetime=match["start_datetime"], team_1__name=match["team_1"],
                                             team_2__name=match["team_2"]).exists()

    @staticmethod
    def create_tournament(match: MatchData) -> Tournament:
        """
        Based on the information in the given match, create a Tournament object and return it. If an object for the
        tournament already exists, the existing object is returned.
        """
        raise NotImplementedError

    @staticmethod
    def create_team(match: MatchData, team_name: str) -> Team:
        """
        Based on the information in the given match, create a Team object and return it. If an object for the team
        already exists, the existing object is returned.
        """
        raise NotImplementedError

    @staticmethod
    def create_scheduled_match(match: MatchData, tournament: Tournament, team_1: Team, team_2: Team) -> None:
        """Based on the information in the given match, create a ScheduledMatch object."""
        raise NotImplementedError

    def scrape(self) -> None:
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
            team_1 = self.create_team(match, match["team_1"])
            team_2 = self.create_team(match, match["team_2"])

            self.create_scheduled_match(match, tournament, team_1, team_2)
