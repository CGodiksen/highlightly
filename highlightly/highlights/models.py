from django.core.validators import MinValueValidator
from django.db import models

from scrapers.models import GameVod


class Highlight(models.Model):
    game_vod = models.ForeignKey(GameVod, on_delete=models.CASCADE)

    start_time_seconds = models.IntegerField(validators=[MinValueValidator(0)])
    duration_seconds = models.IntegerField(validators=[MinValueValidator(5)])
    events = models.CharField(max_length=512)
    round_number = models.IntegerField(validators=[MinValueValidator(1)])

    def __str__(self) -> str:
        return f"Round {self.round_number} ({self.duration_seconds}s): {self.events}"
