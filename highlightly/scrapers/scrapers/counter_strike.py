def list_upcoming_matches() -> list:
    """Scrape HLTV for upcoming Counter-Strike matches and return the list of matches."""
    return []


def filter_already_scheduled_matches(matches: list) -> list:
    """Remove the matches from the given list of matches that already have a corresponding ScheduledMatch object."""
    return matches


def create_scheduled_match(match) -> None:
    """Based on the match data and extra information retrieved from the match URL, create a ScheduledMatch object."""
    pass
