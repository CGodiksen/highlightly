from django.contrib import admin

from scrapers.models import Tournament, Team, Match

admin.site.register(Tournament)
admin.site.register(Team)
admin.site.register(Match)
