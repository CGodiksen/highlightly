import random
from pathlib import Path
from typing import Type, TypeVar

from django.db.models import QuerySet, F
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer

from scrapers import serializers
from scrapers import tasks
from scrapers.models import Match, Team, Game
from scrapers.serializers import MatchSerializer
from util.file_util import save_base64_image
from videos.metadata.post_match import finish_video_thumbnail

T = TypeVar("T", bound=ModelSerializer)


class MatchViewSet(mixins.UpdateModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    def get_serializer_class(self) -> Type[T]:
        if self.action == "update":
            return serializers.MatchUpdateSerializer
        else:
            return serializers.MatchSerializer

    def get_queryset(self) -> QuerySet[Match]:
        """Limit the queryset to the game given in the query parameters."""
        if "game" in self.request.query_params:
            return Match.objects.filter(team_1__game=self.request.query_params["game"]).order_by("start_datetime")
        else:
            raise ValidationError({"detail": "Matches cannot be accessed without supplying a game."})

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

        matches = Match.objects.all()
        return Response(MatchSerializer(matches, many=True).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["POST"])
    def scrape_finished_match(self, request: Request, pk: int) -> Response:
        match: Match = get_object_or_404(Match, id=pk)

        if match.team_1.game == Game.COUNTER_STRIKE:
            tasks.scrape_finished_counter_strike_match(pk)
        elif match.team_1.game == Game.LEAGUE_OF_LEGENDS:
            tasks.scrape_finished_league_of_legends_match(pk)
        elif match.team_1.game == Game.VALORANT:
            tasks.scrape_finished_valorant_match(pk)

        match.refresh_from_db()
        return Response(MatchSerializer(match).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["POST"])
    def refresh_match_frame(self, request: Request, pk: int) -> Response:
        match: Match = get_object_or_404(Match, id=pk)

        if match.gamevod_set.count() > 0:
            finish_video_thumbnail(match, match.videometadata, random.randint(30, 500))
        else:
            raise ValidationError("Match does not have any VODs.", code=status.HTTP_403_FORBIDDEN)

        return Response(MatchSerializer(match).data, status=status.HTTP_201_CREATED)


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

            serializer.validated_data["logo_filename"] = new_filename

        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=True, methods=["POST"])
    def refresh_from_url(self, request: Request) -> Response:
        return Response({}, status=status.HTTP_200_OK)
