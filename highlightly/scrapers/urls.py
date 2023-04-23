from django.urls import path, include
from rest_framework import routers

from scrapers import views

router = routers.SimpleRouter()
router.register(r"scheduled_matches", views.MatchViewSet, basename="scheduled-match")

urlpatterns = [
    path('', include(router.urls)),
]
