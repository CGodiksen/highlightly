from django.urls import path

from users import views

app_name = "users"
urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('me/', views.RetrieveMeView.as_view(), name='me'),
]
