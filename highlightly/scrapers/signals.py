import json
import logging
import os
import shutil
from datetime import timedelta

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_celery_beat.models import IntervalSchedule, MINUTES, PeriodicTask

from scrapers.models import Tournament, Match, GOTVDemo, GameVod, Organization, Game


@receiver(post_delete, sender=Tournament)
def delete_tournament_logo(instance: Tournament, **_kwargs) -> None:
    try:
        logging.info(f"{instance} deleted. Also deleting the related tournament logo at {instance.logo_filename}.")
        os.remove(f"media/tournaments/{instance.logo_filename}")
    except OSError:
        pass


@receiver(post_delete, sender=Organization)
def delete_organization_logo(instance: Organization, **_kwargs) -> None:
    try:
        if instance.logo_filename != "default.png":
            logging.info(f"{instance} deleted. Also deleting the related team logo at {instance.logo_filename}.")
            os.remove(f"media/teams/{instance.logo_filename}")
    except OSError:
        pass


@receiver(post_delete, sender=GOTVDemo)
def delete_gotv_demo(instance: GOTVDemo, **_kwargs) -> None:
    try:
        logging.info(f"{instance} deleted. Also deleting the related GOTV demo at {instance.filename}.")
        os.remove(f"{instance.game_vod.match.create_unique_folder_path('demos')}/{instance.filename}")
    except OSError:
        pass


@receiver(post_delete, sender=GameVod)
def delete_vod(instance: GameVod, **_kwargs) -> None:
    try:
        logging.info(f"{instance} deleted. Also deleting the related VOD at {instance.filename}.")
        os.remove(f"{instance.match.create_unique_folder_path('vods')}/{instance.filename}")
    except OSError:
        pass


@receiver(post_delete, sender=GameVod)
def delete_statistics(instance: GameVod, **_kwargs) -> None:
    try:
        logging.info(f"{instance} deleted. Also deleting the related team statistics.")

        folder_path = f"{instance.match.create_unique_folder_path('statistics')}"
        os.remove(f"{folder_path}/{instance.team_1_statistics_filename}")
        os.remove(f"{folder_path}/{instance.team_2_statistics_filename}")
    except OSError:
        pass


@receiver(post_delete, sender=Match)
def delete_match_data(instance: Match, **_kwargs) -> None:
    try:
        logging.info(f"{instance} deleted. Also deleting the match media folder.")

        # Remove the match folder.
        folder_path = instance.create_unique_folder_path()
        shutil.rmtree(folder_path)

        # If it was the last match in the tournament folder, also clean up the tournament folder.
        tournament_folder_path = "/".join(folder_path.split("/")[:-1])
        if len(os.listdir(tournament_folder_path)) == 0:
            shutil.rmtree(tournament_folder_path)
    except OSError:
        pass


@receiver(post_save, sender=Match)
def create_check_match_status_periodic_task(instance: Match, created: bool, **_kwargs) -> None:
    """Create a periodic task that starts checking the match status after the game is started."""
    # TODO: Also create a task for Counter-Strike and League of Legends matches.
    if created and instance.team_1.game == Game.VALORANT:
        logging.info(f"{instance} created. Creating periodic task to check the match status when it is started.")

        schedule, _ = IntervalSchedule.objects.get_or_create(every=5, period=MINUTES)
        task = f"scrapers.tasks.check_match_status"

        PeriodicTask.objects.create(name=f"Check {instance} status", kwargs=json.dumps({"match_id": instance.id}),
                                    interval=schedule, task=task, start_time=instance.start_datetime)
