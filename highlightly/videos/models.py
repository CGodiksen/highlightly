from django.db import models

from scrapers.models import ScheduledMatch


class VideoMetadata(models.Model):
    scheduled_match = models.ForeignKey(ScheduledMatch, on_delete=models.CASCADE)

    title = models.CharField(max_length=100)
    description = models.TextField(max_length=5000)
    tags = models.JSONField()
    thumbnail_filename = models.CharField(max_length=256)

    language = models.CharField(max_length=256, default="english")
    category_id = models.IntegerField(default=20)

    def __str__(self) -> str:
        return self.title
