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
    path("matches/<int:pk>/", views.MatchDetailView.as_view(), name="match_detail"),
    path("matches/<int:pk>/update_match/", views.EditMatchView.as_view(), name="update_match"),
    path("matches/<int:pk>/delete_match/", views.DeleteMatchView.as_view(), name="delete_match"),
    path("signup/", views.OfficerSignUpView.as_view(), name="signup"),
    # Username and password live on one page. django.contrib.auth.urls also
    # routes /accounts/password_change/ to Django's own view; config/urls.py
    # shadows that URL with a redirect here so there is a single place to
    # change either one.
    path("account/", views.AccountView.as_view(), name="account"),
]
