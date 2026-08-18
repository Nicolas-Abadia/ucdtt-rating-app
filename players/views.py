from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django.views import generic
from django.urls import reverse_lazy
from ratings.services import recompute_all_ratings
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
        Edit one existing player in the database.

        rating is deliberately not editable here, because it is derived
        data: every recompute resets each player to initial_rating and
        replays the matches, so a hand-edited rating would be silently
        discarded the next time that happens, and it would leave no
        RatingHistory row explaining the jump.

        initial_rating is the officer-settable knob instead (it is what a
        player is seeded with), and changing it triggers a recompute so it
        takes effect immediately rather than at some unrelated later one.
    """
    model = Player
    fields = ["name", "initial_rating"]
    success_url = reverse_lazy("players:index")

    def form_valid(self, form):
        response = super().form_valid(form)
        if "initial_rating" in form.changed_data:
            recompute_all_ratings()
        return response

class DeletePlayerView(LoginRequiredMixin, generic.DeleteView):
    """
        Delete one existing player in the database.

        Player is PROTECTed by Match.player1/player2, so deleting someone
        who has already played raises ProtectedError. Refusing is the
        right outcome, since their matches are what every opponent's
        rating was computed from, but unhandled it surfaces as a 500. It's
        caught here and reported back as a message instead.
    """
    model = Player
    success_url = reverse_lazy("players:index")

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                f"\u201c{self.object.name}\u201d can't be deleted because they have "
                "recorded matches. Those matches are what the other players' "
                "ratings were computed from.",
            )
            return redirect("players:detail", pk=self.object.pk)

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

class DeleteMatchView(LoginRequiredMixin, generic.DeleteView):
    """
        Delete a match. Ratings are replayed from the remaining matches in
        Match.delete() (see players/models.py), so the deleted match stops
        affecting every rating it fed into, not just the two players'
        current numbers.
    """
    model = Match
    template_name = "players/match_confirm_delete.html"
    success_url = reverse_lazy("players:matches")
