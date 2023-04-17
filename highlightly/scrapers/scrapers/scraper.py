class Scraper:
    @staticmethod
    def list_upcoming_matches() -> list:
        """Scrape for upcoming matches and return the list of found matches."""
        raise NotImplementedError

    @staticmethod
    def filter_already_scheduled_matches(matches: list) -> list:
        """Remove the matches from the given list of matches that already have a corresponding ScheduledMatch object."""
        raise NotImplementedError

    @staticmethod
    def create_scheduled_match(match) -> None:
        raise NotImplementedError

    def scrape(self) -> None:
        """
        Scrape for upcoming matches. For each new match that is found, a ScheduledMatch object is reated. If the match
        already exists, the match is ignored.
        """
        # List the current upcoming matches in HLTV.
        matches = self.list_upcoming_matches()
        new_matches = self.filter_already_scheduled_matches(matches)

        # For each remaining match in the list, create a ScheduledMatch object.
        for match in new_matches:
            # TODO: When a scheduled match is created a websocket message should be sent.
            self.create_scheduled_match(match)
