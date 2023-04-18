from typing import Type, TypeVar

from django.db.models import QuerySet
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer

from scrapers import tasks
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

    @action(detail=False, methods=["POST"])
    def scrape(self, request: Request) -> Response:
        tasks.scrape_counter_strike_matches.delay()
        tasks.scrape_league_of_legends_matches.delay()
        tasks.scrape_valorant_matches.delay()

        return Response({}, status=status.HTTP_200_OK)
