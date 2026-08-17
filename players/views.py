from django.views import generic
from .models import Player, Match
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

class EditPlayerView(generic.UpdateView):
    """
        Edit one existing player in the database
    """
    model = Player
    fields = ["name", "rating"]
    success_url = reverse_lazy("players:index")

class DeletePlayerView(generic.DeleteView):
    """
        Delete one existing player in the database
    """
    model = Player
    success_url = reverse_lazy("players:index")

class MatchListView(generic.ListView):
    """
        Return list of all matches in record
    """
    model = Match
    ordering = "-date"
    template_name = "players/match_list.html"
    context_object_name = "match_list"

class LogMatchView(generic.CreateView):
    """
        Add new match
    """
    model = Match
    fields = ["player1", "player2", "score1", "score2", "date"]
    template_name = "players/match_form.html"
    success_url = reverse_lazy("players:matches")
