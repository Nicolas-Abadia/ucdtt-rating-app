from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import generic
from django.urls import reverse_lazy
from .models import Player, Match
from .forms import MatchForm, OfficerSignUpForm

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

class OfficerSignUpView(LoginRequiredMixin, generic.CreateView):
    """
        Create a new officer account. Requires an existing officer to be
        logged in, since v1 has officer-only accounts and no public
        self-registration.
    """
    form_class = OfficerSignUpForm
    template_name = "players/signup.html"
    success_url = reverse_lazy("players:index")

class AddPlayerView(LoginRequiredMixin, generic.CreateView):
    """
        Adds a player to the database
    """
    model = Player
    fields = ["name", "rating"]
    success_url = reverse_lazy("players:index")

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.initial_rating = self.object.rating
        self.object.save()
        return response

class EditPlayerView(LoginRequiredMixin, generic.UpdateView):
    """
        Edit one existing player in the database
    """
    model = Player
    fields = ["name", "rating"]
    success_url = reverse_lazy("players:index")

class DeletePlayerView(LoginRequiredMixin, generic.DeleteView):
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

class LogMatchView(LoginRequiredMixin, generic.CreateView):
    """
        Add new match. Rating updates happen in Match.save() (see
        players/models.py), so they apply for any Match creation (this
        view, the admin, the shell, etc), not just this view.
    """
    model = Match
    form_class = MatchForm
    template_name = "players/match_form.html"
    success_url = reverse_lazy("players:matches")
