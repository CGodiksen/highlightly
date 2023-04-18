from typing import Type, TypeVar

from django.db.models import QuerySet
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer

from scrapers import tasks
from scrapers import serializers
from scrapers.models import ScheduledMatch

T = TypeVar("T", bound=ModelSerializer)


class ScheduledMatchViewSet(mixins.UpdateModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    def get_serializer_class(self) -> Type[T]:
        if self.action == "update":
            return serializers.ScheduledMatchUpdateSerializer
        else:
            return serializers.ScheduledMatchSerializer

    def get_queryset(self) -> QuerySet[ScheduledMatch]:
        return ScheduledMatch.objects.all().order_by("-start_datetime")

    @action(detail=False, methods=["POST"])
    def scrape(self, request: Request) -> Response:
        serializer = serializers.ScrapeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if "game" not in serializer.validated_data or serializer.validated_data["game"] == "counter-strike":
            tasks.scrape_counter_strike_matches()

        if "game" not in serializer.validated_data or serializer.validated_data["game"] == "league-of-legends":
            tasks.scrape_league_of_legends_matches.delay()

        if "game" not in serializer.validated_data or serializer.validated_data["game"] == "valorant":
            tasks.scrape_valorant_matches.delay()

        return Response({}, status=status.HTTP_200_OK)
