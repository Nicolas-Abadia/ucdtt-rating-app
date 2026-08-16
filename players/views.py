from django.views import generic
from .models import Player
from django.urls import reverse_lazy

# Create your views here.


class PlayerIndexView(generic.ListView):
    """
        Return a list of all players registered in the system ordered by rating.
    """
    model = Player
    ordering = "-rating"
    template_name = "players/index.html"
    context_object_name = "player_list"


class PlayerDetailView(generic.DetailView):
    """
        Shows the detailed information of a player.
    """
    model = Player
    template_name = "players/detail.html"
    context_object_name = "player"

class AddPlayerView(generic.CreateView):
    """
        Adds a player to the database
    """
    model = Player
    fields = ["name", "rating"]
    success_url = reverse_lazy("players:index")
