from django.urls import path, include
from rest_framework import routers

from videos import views

router = routers.SimpleRouter()
router.register(r"video-metadatas", views.VideoMetadataViewSet, basename="video-metadata")

urlpatterns = [
    path('', include(router.urls)),
]
