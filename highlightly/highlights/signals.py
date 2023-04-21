from django.db.models.signals import post_save
from django.dispatch import receiver

from scrapers.models import ScheduledMatch


@receiver(post_save, sender=ScheduledMatch)
def create_check_if_match_finished_periodic_task(instance: ScheduledMatch, created: bool, **_kwargs) -> None:
    """Create a periodic task that starts checking if the game is finished after the estimated end datetime."""
    if created:
        pass
