from django.db.models.signals import post_save
from django.dispatch import receiver

from highlights.highlighters.counter_strike import CounterStrikeHighlighter
from highlights.highlighters.league_of_legends import LeagueOfLegendsHighlighter
from highlights.highlighters.valorant import ValorantHighlighter
from scrapers.models import Match, Game


@receiver(post_save, sender=Match)
def create_highlights(instance: Match, update_fields: frozenset, **_kwargs) -> None:
    if "finished" in update_fields:
        if instance.team_1.game == Game.COUNTER_STRIKE:
            highlighter = CounterStrikeHighlighter()
        elif instance.team_1.game == Game.VALORANT:
            highlighter = ValorantHighlighter()
        else:
            highlighter = LeagueOfLegendsHighlighter()

        highlighter.highlight(instance)
