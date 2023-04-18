from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Game(models.TextChoices):
    COUNTER_STRIKE = "COUNTER_STRIKE", "Counter-Strike"
    LEAGUE_OF_LEGENDS = "LEAGUE_OF_LEGENDS", "League of Legends"
    VALORANT = "VALORANT", "Valorant"


class Tournament(models.Model):
    game = models.CharField(max_length=32, choices=Game.choices)
    name = models.CharField(max_length=128)

    logo_filename = models.CharField(max_length=256, blank=True, null=True)
    url = models.URLField(max_length=128, blank=True, null=True)


class Team(models.Model):
    game = models.CharField(max_length=32, choices=Game.choices)
    name = models.CharField(max_length=128)
    logo_filename = models.CharField(max_length=256)

    nationality = models.CharField(max_length=256)
    ranking = models.IntegerField(validators=[MinValueValidator(1)])
    url = models.URLField(max_length=128)


# TODO: When a scheduled match is created a websocket message should be sent.
# TODO: A new task to create metadata for the video related to the match should also be started.
# TODO: A django celery beat periodic task should also be started to check for if the video is done.
class ScheduledMatch(models.Model):
    class Meta:
        verbose_name_plural = "Scheduled matches"

    class Format(models.TextChoices):
        BEST_OF_1 = "BEST_OF_1", "Bo1"
        BEST_OF_3 = "BEST_OF_3", "Bo3"
        BEST_OF_5 = "BEST_OF_5", "Bo5"

    team_1 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="scheduled_team_1_matches")
    team_2 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="scheduled_team_2_matches")
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    tournament_context = models.CharField(max_length=64)
    format = models.CharField(max_length=16, choices=Format.choices)
    tier = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    url = models.URLField(max_length=128)

    created_at = models.DateTimeField(auto_now_add=True)
    start_datetime = models.DateTimeField()
    estimated_end_datetime = models.DateTimeField()

    create_video = models.BooleanField()
    finished = models.BooleanField(default=False)
