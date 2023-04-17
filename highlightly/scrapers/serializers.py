from rest_framework import serializers

from scrapers.models import ScheduledMatch, Tournament
from util.file_util import get_base64


class TournamentSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Tournament
        fields = ["id", "game", "name", "logo", "url"]

    @staticmethod
    def get_logo(tournament: Tournament) -> str:
        return get_base64(tournament.logo_filename)
