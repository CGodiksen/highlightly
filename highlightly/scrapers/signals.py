import json
import os

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_celery_beat.models import IntervalSchedule, PeriodicTask, MINUTES

from scrapers.models import Tournament, Team, Match


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


@receiver(post_save, sender=Match)
def create_scrape_finished_match_periodic_task(instance: Match, created: bool, **_kwargs) -> None:
    """Create a periodic task that starts trying to scrape the finished match after the estimated end datetime."""
    if created and instance.create_video:
        task = f"scrapers.tasks.scrape_finished_{instance.team_1.game.lower()}_match"
        keyword_args = {"scheduled_match_id": instance.id}

        schedule, _ = IntervalSchedule.objects.get_or_create(every=5, period=MINUTES)
        PeriodicTask.objects.create(name=f"Scrape {instance} if finished", kwargs=json.dumps(keyword_args),
                                    interval=schedule, task=task, start_time=instance.estimated_end_datetime)
