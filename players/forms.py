from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from . import imports
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


class CsvUploadForm(forms.Form):
    """
    Officer-facing upload, shared by both CSV imports.

    Only the file is asked for. Whether to write is not a field here: an
    upload always produces a preview, and the import is confirmed from that
    preview without picking the file a second time. See
    players.views.CsvImportView.

    The extension check is not security: content type is client-supplied and
    an extension proves nothing. It exists to catch the ordinary mistake of
    picking the .xlsx instead of the exported .csv, which would otherwise
    fail as an unreadable-encoding error.
    """

    csv_file = forms.FileField(
        label="CSV file",
        help_text="A .csv file exported from Excel, Google Sheets or similar.",
    )

    def clean_csv_file(self):
        upload = self.cleaned_data["csv_file"]
        if not upload.name.lower().endswith(".csv"):
            raise forms.ValidationError("That is not a .csv file.")
        if upload.size > imports.MAX_UPLOAD_BYTES:
            limit = imports.MAX_UPLOAD_BYTES // (1024 * 1024)
            raise forms.ValidationError(f"That file is larger than {limit} MB.")
        return upload


class UsernameChangeForm(forms.ModelForm):
    """
    Renames the officer account that is already signed in.

    Uniqueness is enforced by User.username at the database level, but going
    through a ModelForm is what turns a collision into a field error on the
    page instead of the IntegrityError a bare save would raise. ModelForm
    also excludes the current instance from that check, so re-saving the
    same name is not reported as taken.

    Only the username. The password half of the account page is Django's
    PasswordChangeForm, which already requires the old password, runs the
    configured validators, and keeps the session signed in. See
    players.views.AccountView, which submits both forms together.
    """

    class Meta:
        model = User
        fields = ["username"]
        labels = {"username": "Username"}
        help_texts = {
            "username": "Used to sign in. Letters, digits and @ . + - _ only.",
        }

    
