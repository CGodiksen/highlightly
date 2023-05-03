from pathlib import Path
from typing import Type, TypeVar

from django.db.models import QuerySet, F
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
        return Team.objects.all().order_by(F("ranking").asc(nulls_last=True))

    def update(self, request: Request, *args, **kwargs) -> Response:
        instance: Team = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        # If a new logo is provided, replace the old image in local storage.
        if "logo_base64" in serializer.validated_data and serializer.validated_data["logo_base64"]:
            if instance.logo_filename != "default.png":
                Path(f"media/teams/{instance.logo_filename}").unlink(missing_ok=True)

            new_filename = f"{serializer.validated_data['name'].replace(' ', '_')}.png"
            base64: str = serializer.validated_data["logo_base64"]
            save_base64_image(f"media/teams/{new_filename}", base64)

            instance.logo_filename = new_filename
            instance.save()

        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=True, methods=["POST"])
    def refresh_from_url(self, request: Request) -> Response:
        return Response({}, status=status.HTTP_200_OK)
