from django.db.models.signals import post_save
from django.dispatch import receiver

from scrapers.models import Match
from videos.metadata.post_match import add_post_match_video_metadata
from videos.metadata.pre_match import create_pre_match_video_metadata


@receiver(post_save, sender=Match)
def create_match_video_metadata(instance: Match, created: bool, update_fields: frozenset, **_kwargs) -> None:
    if created:
        create_pre_match_video_metadata(instance)
    elif "finished" in update_fields and instance.finished:
        add_post_match_video_metadata(instance)
