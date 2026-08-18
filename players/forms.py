from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Match, Player


class OfficerSignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "password1", "password2"]


class PlayerForm(forms.ModelForm):
    """
    Shared by AddPlayerView and EditPlayerView so the two can't drift apart
    and show different fields for the same thing.

    Only initial_rating is exposed. rating is derived: every recompute
    resets each player to initial_rating and replays the matches, so a
    hand-set rating would be silently discarded (see EditPlayerView).
    """

    class Meta:
        model = Player
        fields = ["name", "initial_rating"]
        labels = {"initial_rating": "Starting rating"}
        help_texts = {
            "initial_rating": "The rating this player starts from, before any matches are counted.",
        }


class MatchForm(forms.ModelForm):
    date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        ),
        # Accept the browser's datetime-local format (with "T") as well as
        # Django's regular datetime formats, in case the field is ever
        # posted to some other way (e.g. existing tests, the API later on).
        input_formats=[
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
        ],
        label="Date and time",
        help_text="Pick the date and time the match was played, or use the \u201cUse current date/time\u201d button below.",
    )

    class Meta:
        model = Match
        fields = ["player1", "player2", "score1", "score2", "date"]

    def clean(self):
        cleaned_data = super().clean()
        player1 = cleaned_data.get("player1")
        player2 = cleaned_data.get("player2")
        score1 = cleaned_data.get("score1")
        score2 = cleaned_data.get("score2")
        date = cleaned_data.get("date")

        if player1 and player2 and player1 == player2:
            raise forms.ValidationError("A player cannot play against themselves.")

        if score1 is not None and score1 < 0:
            self.add_error("score1", "Score cannot be negative.")
        if score2 is not None and score2 < 0:
            self.add_error("score2", "Score cannot be negative.")

        if score1 is not None and score2 is not None and score1 == score2:
            raise forms.ValidationError("A match cannot end in a tie; one player must win more games.")

        if date and date > timezone.now():
            self.add_error("date", "Match date cannot be in the future.")

        return cleaned_data
