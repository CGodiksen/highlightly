from typing import Type, TypeVar

from django.db.models import QuerySet
from rest_framework import mixins, viewsets
from rest_framework.serializers import ModelSerializer

from videos import serializers
from videos.models import VideoMetadata

T = TypeVar("T", bound=ModelSerializer)


class VideoMetadataViewSet(mixins.UpdateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    def get_serializer_class(self) -> Type[T]:
        if self.action == "update":
            return serializers.VideoMetadataUpdateSerializer
        else:
            return serializers.VideoMetadataSerializer

    def get_queryset(self) -> QuerySet[VideoMetadata]:
        return VideoMetadata.objects.all()
