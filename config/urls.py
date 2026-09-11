"""
Root URL configuration.

Order matters: the players app owns the site root, then two auth URLs are
shadowed so the account page is the only place a password changes, then the
rest of django.contrib.auth.urls, then the admin.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from players.api import OfficerCreateView, router
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("api/", include(router.urls)),
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
    # Officers create further officer accounts; no public self-registration.
    path("api/officers/", OfficerCreateView.as_view(), name="officer_create"),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Logout invalidates the refresh token server-side, not just client-side.
    path("api/token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),
]
