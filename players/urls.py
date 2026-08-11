from django.urls import path

from . import views

app_name = "players"

urlpatterns = [
    path("", views.PlayerIndexView.as_view(), name="index"),
    path("<int:pk>/", views.PlayerDetailView.as_view(), name="detail"),
]
