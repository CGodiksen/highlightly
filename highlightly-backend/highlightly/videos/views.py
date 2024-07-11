from typing import TypeVar

from rest_framework.generics import UpdateAPIView
from rest_framework.serializers import ModelSerializer

from videos import serializers
from videos.models import VideoMetadata

T = TypeVar("T", bound=ModelSerializer)


class UpdateVideoMetadata(UpdateAPIView):
    serializer_class = serializers.VideoMetadataUpdateSerializer
    queryset = VideoMetadata.objects.all()
