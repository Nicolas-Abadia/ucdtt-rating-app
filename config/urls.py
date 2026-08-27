"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
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
