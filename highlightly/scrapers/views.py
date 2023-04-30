from typing import Type, TypeVar

from django.db.models import QuerySet
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer

from scrapers import serializers
from scrapers import tasks
from scrapers.models import Match, Team

T = TypeVar("T", bound=ModelSerializer)


class MatchViewSet(mixins.UpdateModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    def get_serializer_class(self) -> Type[T]:
        if self.action == "update":
            return serializers.MatchUpdateSerializer
        else:
            return serializers.MatchSerializer

    def get_queryset(self) -> QuerySet[Match]:
        return Match.objects.all().order_by("-start_datetime")

    @action(detail=False, methods=["POST"])
    def scrape_matches(self, request: Request) -> Response:
        serializer = serializers.ScrapeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if "game" not in serializer.validated_data or serializer.validated_data["game"] == "counter-strike":
            tasks.scrape_counter_strike_matches()

        if "game" not in serializer.validated_data or serializer.validated_data["game"] == "league-of-legends":
            tasks.scrape_league_of_legends_matches()

        if "game" not in serializer.validated_data or serializer.validated_data["game"] == "valorant":
            tasks.scrape_valorant_matches()

        return Response({}, status=status.HTTP_200_OK)


class TeamViewSet(mixins.UpdateModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    def get_serializer_class(self) -> Type[T]:
        if self.action == "update":
            return serializers.TeamUpdateSerializer
        else:
            return serializers.TeamSerializer

    def get_queryset(self) -> QuerySet[Team]:
        return Team.objects.all().order_by("-ranking")
