from django.urls import path, include
from rest_framework import routers

from scrapers import views

router = routers.SimpleRouter()
router.register(r"matches", views.MatchViewSet, basename="match")
router.register(r"teams", views.TeamViewSet, basename="team")

urlpatterns = [
    path('', include(router.urls)),
]
