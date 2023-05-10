from django.urls import path

from videos import views

urlpatterns = [
    path('video-metadata/', views.UpdateVideoMetadata.as_view(), name="video_metadata"),
]
