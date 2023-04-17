from rest_framework import serializers

from scrapers.models import Tournament, Team, ScheduledMatch
from util.file_util import get_base64


class TournamentSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Tournament
        fields = ["id", "game", "name", "logo", "url"]

    @staticmethod
    def get_logo(tournament: Tournament) -> str:
        return get_base64(tournament.logo_filename)


class TeamSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ["id", "game", "name", "logo", "nationality", "ranking", "url"]

    @staticmethod
    def get_logo(tournament: Tournament) -> str:
        return get_base64(tournament.logo_filename)


class ScheduledMatchSerializer(serializers.ModelSerializer):
    team_1 = TeamSerializer()
    team_2 = TeamSerializer()
    tournament = TournamentSerializer()

    class Meta:
        model = ScheduledMatch
        fields = ["id", "team_1", "team_2", "tournament", "tournament_context", "type", "tier", "url", "created_at",
                  "start_time", "estimated_end_time", "create_video", "finished"]
