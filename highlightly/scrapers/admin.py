from django.contrib import admin

from scrapers.models import Tournament, Team, Match, GameVod, GOTVDemo, Player

admin.site.register(Tournament)
admin.site.register(Team)
admin.site.register(Player)
admin.site.register(Match)
admin.site.register(GameVod)
admin.site.register(GOTVDemo)
