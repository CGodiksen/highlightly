from typing import Type, TypeVar

from django.db.models import QuerySet
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.serializers import ModelSerializer

from scrapers.models import ScheduledMatch
from scrapers.serializers import ScheduledMatchUpdateSerializer, ScheduledMatchSerializer

T = TypeVar("T", bound=ModelSerializer)


class ScheduledMatchRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    def get_queryset(self) -> QuerySet[ScheduledMatch]:
        return ScheduledMatch.objects.all()

    def get_serializer_class(self) -> Type[T]:
        if self.request.method == "PUT" or self.request.method == "PATCH":
            return ScheduledMatchUpdateSerializer
        else:
            return ScheduledMatchSerializer
