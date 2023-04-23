from django.db.models.signals import post_save
from django.dispatch import receiver

from scrapers.models import Match
from videos.metadata.pre_match import create_pre_match_video_metadata


@receiver(post_save, sender=Match)
def create_match_video_metadata(instance: Match, created: bool, **_kwargs) -> None:
    if created:
        create_pre_match_video_metadata(instance)
