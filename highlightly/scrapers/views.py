from typing import Type, TypeVar

from django.db.models import QuerySet
from rest_framework import mixins, viewsets
from rest_framework.serializers import ModelSerializer

from scrapers.models import ScheduledMatch
from scrapers.serializers import ScheduledMatchUpdateSerializer, ScheduledMatchSerializer

T = TypeVar("T", bound=ModelSerializer)


class ScheduledMatchViewSet(mixins.UpdateModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    def get_serializer_class(self) -> Type[T]:
        if self.action == "update":
            return ScheduledMatchUpdateSerializer
        else:
            return ScheduledMatchSerializer

    def get_queryset(self) -> QuerySet[ScheduledMatch]:
        return ScheduledMatch.objects.all().order_by("-start_time")
