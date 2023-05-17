from rest_framework import serializers

from scrapers.models import Tournament, Team, Match
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
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ["id", "game", "name", "logo", "nationality", "ranking", "url", "background_color"]

    @staticmethod
    def get_logo(team: Team) -> str:
        return get_base64(f"media/teams/{team.organization.logo_filename}")


class TeamUpdateSerializer(serializers.ModelSerializer):
    logo_base64 = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Team
        fields = ["name", "nationality", "ranking", "url", "background_color", "logo_base64"]

    def to_representation(self, team: Team) -> dict:
        return TeamSerializer(team).data


class MatchSerializer(serializers.ModelSerializer):
    team_1 = TeamSerializer()
    team_2 = TeamSerializer()
    tournament = serializers.StringRelatedField()
    video_metadata = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = ["id", "team_1", "team_2", "tournament", "tournament_context", "format", "tier", "url", "created_at",
                  "start_datetime", "estimated_end_datetime", "create_video", "finished", "highlighted",
                  "video_metadata"]

    @staticmethod
    def get_video_metadata(match: Match) -> dict:
        return VideoMetadataSerializer(match.videometadata).data


class MatchUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = ["create_video"]


class ScrapeSerializer(serializers.Serializer):
    game = serializers.ChoiceField(choices=["counter-strike", "valorant", "league-of-legends"], required=False)
