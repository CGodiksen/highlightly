import json
import logging
import os

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_celery_beat.models import IntervalSchedule, PeriodicTask, MINUTES

from scrapers.models import Tournament, Team, Match


@receiver(post_delete, sender=Tournament)
def delete_tournament_logo(instance: Tournament, **_kwargs) -> None:
    try:
        logging.info(f"{instance} deleted. Also deleting the related tournament logo at {instance.logo_filename}.")
        os.remove(f"media/tournaments/{instance.logo_filename}")
    except OSError:
        pass


@receiver(post_delete, sender=Team)
def delete_team_logo(instance: Team, **_kwargs) -> None:
    try:
        if instance.logo_filename != "default.png":
            logging.info(f"{instance} deleted. Also deleting the related team logo at {instance.logo_filename}.")
            os.remove(f"media/teams/{instance.logo_filename}")
    except OSError:
        pass


@receiver(post_save, sender=Match)
def create_scrape_finished_match_periodic_task(instance: Match, created: bool, **_kwargs) -> None:
    """Create a periodic task that starts trying to scrape the finished match after the estimated end datetime."""
    if created and instance.create_video:
        logging.info(f"{instance} created. Creating periodic task to scrape the match when it is finished.")

        task = f"scrapers.tasks.scrape_finished_{instance.team_1.game.lower()}_match"
        keyword_args = {"scheduled_match_id": instance.id}

        schedule, _ = IntervalSchedule.objects.get_or_create(every=10, period=MINUTES)
        PeriodicTask.objects.create(name=f"Scrape {instance} if finished", kwargs=json.dumps(keyword_args),
                                    interval=schedule, task=task, start_time=instance.estimated_end_datetime)
