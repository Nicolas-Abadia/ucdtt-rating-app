from django.urls import path

from . import views

app_name = "players"

urlpatterns = [
    path("", views.PlayerIndexView.as_view(), name="index"),
    path("<int:pk>/", views.PlayerDetailView.as_view(), name="detail"),
    path("new_player/", views.AddPlayerView.as_view(), name="new"),
    path("<int:pk>/delete_player/", views.DeletePlayerView.as_view(), name="delete"),
    path("<int:pk>/update_player/", views.EditPlayerView.as_view(), name="update"),
    path("matches/", views.MatchListView.as_view(), name="matches"),
    path("matches/new_match/", views.LogMatchView.as_view(), name="new_match"),
    path("signup/", views.OfficerSignUpView.as_view(), name="signup"),
]
