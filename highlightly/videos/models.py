from django.core.validators import MinValueValidator
from django.db import models

from scrapers.models import Match


class VideoMetadata(models.Model):
    match = models.OneToOneField(Match, on_delete=models.CASCADE)

    title = models.CharField(max_length=100)
    description = models.TextField(max_length=5000)
    tags = models.JSONField()

    thumbnail_filename = models.CharField(max_length=256)
    thumbnail_match_frame_time = models.IntegerField(validators=[MinValueValidator(1)], blank=True, null=True)

    language = models.CharField(max_length=256, default="english")
    category_id = models.IntegerField(default=20)

    def __str__(self) -> str:
        return self.title
