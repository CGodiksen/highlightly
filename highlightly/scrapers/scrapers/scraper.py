from scrapers.types import Match


class Scraper:
    @staticmethod
    def list_upcoming_matches() -> list[Match]:
        """Scrape for upcoming matches and return the list of found matches."""
        raise NotImplementedError

    @staticmethod
    def filter_already_scheduled_matches(matches: list[Match]) -> list[Match]:
        """Remove the matches from the given list of matches that already have a corresponding ScheduledMatch object."""
        raise NotImplementedError

    @staticmethod
    def create_scheduled_match(match: Match) -> None:
        """
        Based on the information in the given match, create a scheduled match object. If the teams or
        tournament in the match does not already exist, corresponding objects are created.
        """
        raise NotImplementedError

    def scrape(self) -> None:
        """
        Scrape for upcoming matches. For each new match that is found, a ScheduledMatch object is created. If the match
        already exists, the match is ignored.
        """
        # List the current upcoming matches in HLTV.
        matches = self.list_upcoming_matches()
        new_matches = self.filter_already_scheduled_matches(matches)

        # For each remaining match in the list, create a ScheduledMatch object.
        for match in new_matches:
            # TODO: When a scheduled match is created a websocket message should be sent.
            # TODO: A new task to create metadata for the video related to the match should also be started.
            # TODO: A django celery beat periodic task should also be started to check for if the video is done.
            self.create_scheduled_match(match)
