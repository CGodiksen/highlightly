from django.db.models.signals import post_save
from django.dispatch import receiver

from scrapers.models import ScheduledMatch
from videos.util import create_pre_match_video_metadata


@receiver(post_save, sender=ScheduledMatch)
def create_match_video_metadata(instance: ScheduledMatch, created: bool, **_kwargs) -> None:
    if created:
        create_pre_match_video_metadata(instance)
