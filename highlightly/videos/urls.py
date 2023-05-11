from django.urls import path

from videos import views

urlpatterns = [
    path('video_metadata/<int:pk>/', views.UpdateVideoMetadata.as_view(), name="video_metadata"),
]
