from django.urls import path

from scrapers import views

urlpatterns = [
    path('scheduled_match/', views.ScheduledMatchRetrieveUpdateDestroyView.as_view(), name='scheduled_matches'),
]
