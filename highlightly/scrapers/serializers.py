from rest_framework import serializers

from scrapers.models import Tournament, Team, Match, Organization
from util.file_util import get_base64
from videos.serializers import VideoMetadataSerializer


class TournamentSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Tournament
        fields = ["id", "game", "name", "logo", "url"]

    @staticmethod
    def get_logo(tournament: Tournament) -> str:
        return get_base64(f"media/tournaments/{tournament.logo_filename}")


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "game", "nationality", "ranking", "url"]


class OrganizationSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    teams = TeamSerializer(many=True)

    class Meta:
        model = Organization
        fields = ["id", "name", "logo", "background_color", "teams"]

    @staticmethod
    def get_logo(organization: Organization) -> str:
        return get_base64(f"media/teams/{organization.logo_filename}")


class OrganizationUpdateSerializer(serializers.ModelSerializer):
    logo_base64 = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Organization
        fields = ["name", "background_color", "logo_base64"]

    def to_representation(self, organization: Organization) -> dict:
        return OrganizationSerializer(organization).data


class MatchSerializer(serializers.ModelSerializer):
    team_1 = TeamSerializer()
    team_2 = TeamSerializer()
    tournament = serializers.StringRelatedField()
    video_metadata = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = ["id", "team_1", "team_2", "tournament", "tournament_context", "format", "tier", "url", "created_at",
                  "start_datetime", "estimated_end_datetime", "create_video", "finished", "video_metadata"]

    @staticmethod
    def get_video_metadata(match: Match) -> dict:
        return VideoMetadataSerializer(match.videometadata).data


class MatchUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = ["create_video"]


class ScrapeSerializer(serializers.Serializer):
    game = serializers.ChoiceField(choices=["counter-strike", "valorant", "league-of-legends"], required=False)
