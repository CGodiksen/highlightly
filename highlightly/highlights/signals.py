import json

from django.db.models.signals import post_save
from django.dispatch import receiver
from django_celery_beat.models import IntervalSchedule, MINUTES, PeriodicTask

from scrapers.models import ScheduledMatch


@receiver(post_save, sender=ScheduledMatch)
def create_check_if_match_finished_periodic_task(instance: ScheduledMatch, created: bool, **_kwargs) -> None:
    """Create a periodic task that starts checking if the game is finished after the estimated end datetime."""
    if created:
        keyword_args = {"scheduled_match_id": instance.id}

        schedule, _ = IntervalSchedule.objects.get_or_create(every=3, period=MINUTES)
        PeriodicTask.objects.create(name=f"Check if {instance} is finished", kwargs=json.dumps(keyword_args),
                                    interval=schedule, task="highlights.tasks.check_if_match_finished",
                                    start_time=instance.estimated_end_datetime)
