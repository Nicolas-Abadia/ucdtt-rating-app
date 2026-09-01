"""
Root URL configuration.

Order matters: the players app owns the site root, then two auth URLs are
shadowed so the account page is the only place a password changes, then the
rest of django.contrib.auth.urls, then the admin.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("", include("players.urls")),
    # django.contrib.auth.urls routes password_change and its done page to
    # Django's own views. The account page covers both the username and the
    # password, so those two URLs are shadowed here to keep one entry point.
    # URL resolution takes the first match, so these win over the include
    # below. Left unnamed on purpose, so the built-in "password_change" and
    # "password_change_done" names still resolve.
    path(
        "accounts/password_change/",
        RedirectView.as_view(pattern_name="players:account", permanent=False),
    ),
    path(
        "accounts/password_change/done/",
        RedirectView.as_view(pattern_name="players:account", permanent=False),
    ),
    path("accounts/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
]
