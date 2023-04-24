from scrapers.models import Match


class Highlighter:
    def highlight(self, match: Match) -> None:
        """Extract events from the match and combine events to find match highlights."""
        print(f"Create highlights for {str(match)}")
