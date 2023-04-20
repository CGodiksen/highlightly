import os

from django.db.models.signals import post_delete
from django.dispatch import receiver

from scrapers.models import Tournament, Team


@receiver(post_delete, sender=Tournament)
def delete_tournament_logo(instance: Tournament, **_kwargs) -> None:
    try:
        os.remove(f"media/tournaments/{instance.logo_filename}")
    except OSError:
        pass


@receiver(post_delete, sender=Team)
def delete_tournament_logo(instance: Team, **_kwargs) -> None:
    try:
        os.remove(f"media/teams/{instance.logo_filename}")
    except OSError:
        pass
