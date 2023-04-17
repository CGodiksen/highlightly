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
