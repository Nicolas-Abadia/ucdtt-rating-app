from django.views import generic
from .models import Player

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
    model = Player
    template_name = "players/detail.html"
    context_object_name = "player"
