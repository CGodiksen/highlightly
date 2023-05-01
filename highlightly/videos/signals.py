import logging
import os

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from scrapers.models import Match, Game
from videos.editors.counter_strike import CounterStrikeEditor
from videos.editors.league_of_legends import LeagueOfLegendsEditor
from videos.editors.valorant import ValorantEditor
from videos.metadata.post_match import add_post_match_video_metadata
from videos.metadata.pre_match import create_pre_match_video_metadata
from videos.models import VideoMetadata


@receiver(post_save, sender=Match)
def create_match_video_metadata(instance: Match, created: bool, update_fields: frozenset, **_kwargs) -> None:
    if created:
        create_pre_match_video_metadata(instance)
    elif update_fields is not None:
        if "finished" in update_fields and instance.finished:
            add_post_match_video_metadata(instance)
        elif "highlighted" in update_fields and instance.highlighted:
            if instance.team_1.game == Game.COUNTER_STRIKE:
                editor = CounterStrikeEditor()
            elif instance.team_1.game == Game.VALORANT:
                editor = ValorantEditor()
            else:
                editor = LeagueOfLegendsEditor()

            editor.edit_and_upload_video(instance)


@receiver(post_delete, sender=VideoMetadata)
def delete_thumbnail(instance: VideoMetadata, **_kwargs) -> None:
    try:
        logging.info(f"{instance} deleted. Also deleting the related thumbnail at {instance.thumbnail_filename}.")
        os.remove(f"media/thumbnails/{instance.match.tournament.name.replace(' ', '_')}/{instance.thumbnail_filename}")
    except OSError:
        pass
