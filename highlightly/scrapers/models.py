from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Game(models.TextChoices):
    COUNTER_STRIKE = "COUNTER_STRIKE", "Counter-Strike"
    LEAGUE_OF_LEGENDS = "LEAGUE_OF_LEGENDS", "League of Legends"
    VALORANT = "VALORANT", "Valorant"


class Tournament(models.Model):
    game = models.CharField(max_length=32, choices=Game.choices)
    name = models.CharField(max_length=128)

    logo_filename = models.CharField(max_length=256)
    url = models.URLField(max_length=128)


class Team(models.Model):
    game = models.CharField(max_length=32, choices=Game.choices)
    name = models.CharField(max_length=128)
    logo_filename = models.CharField(max_length=256)

    nationality = models.CharField(max_length=256)
    ranking = models.IntegerField(validators=[MinValueValidator(1)])
    url = models.URLField(max_length=128)


class ScheduledMatch(models.Model):
    class Meta:
        verbose_name_plural = "Scheduled matches"

    class Type(models.TextChoices):
        BEST_OF_1 = "BEST_OF_1", "Best of 1"
        BEST_OF_3 = "BEST_OF_3", "Best of 3"
        BEST_OF_5 = "BEST_OF_5", "Best of 5"

    team_1 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="scheduled_team_1_matches")
    team_2 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="scheduled_team_2_matches")
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    tournament_context = models.CharField(max_length=64)
    type = models.CharField(max_length=16, choices=Type.choices)
    tier = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    url = models.URLField(max_length=128)

    created_at = models.DateTimeField(auto_now_add=True)
    start_time = models.DateTimeField()
    estimated_end_time = models.DateTimeField()

    create_video = models.BooleanField()
    finished = models.BooleanField(default=False)
