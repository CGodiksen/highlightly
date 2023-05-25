from django.db.models.signals import post_save
from django.dispatch import receiver

from highlights.highlighters.counter_strike import CounterStrikeHighlighter
from highlights.highlighters.league_of_legends import LeagueOfLegendsHighlighter
from highlights.highlighters.valorant import ValorantHighlighter
from scrapers.models import Game, GameVod


@receiver(post_save, sender=GameVod)
def create_highlights(instance: GameVod, update_fields: frozenset, **_kwargs) -> None:
    if update_fields is not None and "finished" in update_fields and instance.finished:
        if instance.match.team_1.game == Game.COUNTER_STRIKE:
            highlighter = CounterStrikeHighlighter()
        elif instance.match.team_1.game == Game.VALORANT:
            highlighter = ValorantHighlighter()
        else:
            highlighter = LeagueOfLegendsHighlighter()

        highlighter.highlight(instance)
