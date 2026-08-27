import io

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django.views import generic
from django.urls import reverse_lazy
from ratings.services import recompute_all_ratings
from . import imports
from .models import Player, Match
from .forms import (
    CsvUploadForm,
    MatchForm,
    OfficerSignUpForm,
    PlayerForm,
    UsernameChangeForm,
)

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

class AccountView(LoginRequiredMixin, generic.TemplateView):
    """
        One page where a signed-in officer changes their username, their
        password, or both in a single submit.

        Two forms on one page rather than one hand-written form: the password
        half is Django's PasswordChangeForm, which already requires the old
        password and runs AUTH_PASSWORD_VALIDATORS. Reimplementing that is how
        validators quietly stop applying.

        The three password fields are required by that form, so they are only
        bound when at least one of them was filled in. Otherwise changing only
        the username would fail on three blank required fields.

        Nothing here takes a user id. It always acts on request.user, because
        a pk in the URL would let any signed-in officer rename or reset any
        other account, including a superuser.
    """
    template_name = "players/account.html"

    PASSWORD_FIELDS = ("old_password", "new_password1", "new_password2")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # setdefault, so a failed POST can hand back its own bound forms with
        # the errors still attached.
        context.setdefault(
            "username_form", UsernameChangeForm(instance=self.request.user)
        )
        context.setdefault(
            "password_form", PasswordChangeForm(user=self.request.user)
        )
        return context

    def post(self, request, *args, **kwargs):
        user = request.user
        changing_password = any(
            request.POST.get(field) for field in self.PASSWORD_FIELDS
        )

        username_form = UsernameChangeForm(data=request.POST, instance=user)
        password_form = (
            PasswordChangeForm(user=user, data=request.POST)
            if changing_password
            else PasswordChangeForm(user=user)
        )

        username_ok = username_form.is_valid()
        password_ok = password_form.is_valid() if changing_password else True

        if not (username_ok and password_ok):
            # One submit, one outcome. Writing whichever half validated would
            # leave the officer renamed with an unchanged password, or the
            # reverse, with only a form error to explain which happened.
            return self.render_to_response(
                self.get_context_data(
                    username_form=username_form,
                    password_form=password_form,
                )
            )

        changed = []
        with transaction.atomic():
            if username_form.has_changed():
                username_form.save()
                changed.append("username")
            if changing_password:
                # Both forms hold the same in-memory user object, so this save
                # carries the new username along rather than overwriting it.
                password_form.save()
                changed.append("password")

        if changing_password:
            # The password hash the session was signed with is gone now, so
            # without this the officer is logged out by their own change.
            update_session_auth_hash(request, user)

        if changed:
            messages.success(
                request, "Updated the " + " and ".join(changed) + "."
            )
        else:
            messages.info(request, "No changes were submitted.")
        return redirect("players:account")

class AddPlayerView(LoginRequiredMixin, generic.CreateView):
    """
        Adds a player to the database.

        Officers set the starting rating (initial_rating); the current
        rating is seeded from it here and is derived from the matches from
        then on. Shares PlayerForm with EditPlayerView so both forms offer
        the same field under the same label.
    """
    model = Player
    form_class = PlayerForm
    success_url = reverse_lazy("players:index")

    def form_valid(self, form):
        # Set before saving so this is one INSERT rather than an insert
        # followed by an update.
        form.instance.rating = form.instance.initial_rating
        return super().form_valid(form)

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
    form_class = PlayerForm
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

class MatchDetailView(generic.DetailView):
    """
        Shows one recorded match, and for officers the edit and delete
        controls for it.

        The controls live here rather than on every row of the match list so
        that acting on a match takes a deliberate step, and so there is one
        place to add match-level detail (the rating change it caused, notes)
        later.
    """
    model = Match
    template_name = "players/match_detail.html"
    context_object_name = "match"

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

class EditMatchView(LoginRequiredMixin, generic.UpdateView):
    """
        Correct a recorded match. Uses the same MatchForm as logging a new
        one, so a correction can't introduce a tie, duplicate players, or a
        future date. Match.save() replays every rating from the corrected
        record, so fixing a score or date also fixes the ratings of any
        later match that was computed from it.
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

class CsvImportView(LoginRequiredMixin, generic.FormView):
    """
        Shared behaviour for the two CSV imports. Subclasses supply the
        columns, the row builder and the writer.

        One view for both means the upload rules, the preview step and the
        skipped-row report cannot drift apart between players and matches.
        The parsing itself lives in players/imports.py, shared with the
        `import_players` and `import_matches` management commands, so the
        browser and the command line accept exactly the same files.

        A preview and a real import take the same path. That is what makes
        the preview trustworthy: the only difference is whether the writer
        runs at the end.
    """
    template_name = "players/csv_import.html"
    form_class = CsvUploadForm

    title = ""
    columns = ()
    example = ""
    notes = ""

    def build(self, rows):
        """Returns (to_create, skipped). Implemented by subclasses."""
        raise NotImplementedError

    def write(self, to_create):
        """Persists the built objects. Implemented by subclasses."""
        raise NotImplementedError

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("title", self.title)
        context.setdefault("columns", self.columns)
        context.setdefault("example", self.example)
        context.setdefault("notes", self.notes)
        return context

    def labels(self, objects):
        # players.imports attaches a label built from the row itself, so
        # reporting an import costs no queries. Reading str(match) here
        # would fetch both players once per row.
        return [getattr(obj, "_label", None) or str(obj) for obj in objects]

    def form_valid(self, form):
        upload = form.cleaned_data["csv_file"]
        # csv requires newline="", and utf-8-sig drops the byte-order mark
        # that spreadsheet exports prepend.
        stream = io.TextIOWrapper(upload, encoding="utf-8-sig", newline="")
        try:
            rows = imports.read_rows(stream, self.columns, upload.name)
            to_create, skipped = self.build(rows)
        except imports.CsvImportError as error:
            # An unusable file is a problem with this field's value, so it
            # belongs on the field rather than in a page-level message.
            form.add_error("csv_file", str(error))
            return self.form_invalid(form)

        preview = form.cleaned_data["preview"]
        if not preview and to_create:
            self.write(to_create)

        labels = self.labels(to_create)
        return self.render_to_response(
            self.get_context_data(
                form=form,
                ran=True,
                preview=preview,
                pending=labels if preview else [],
                created=[] if preview else labels,
                skipped=skipped,
            )
        )

class ImportPlayersView(CsvImportView):
    """
        Bulk roster upload. Officers already had this as a management
        command, which needs a shell and a database URL; this is the same
        import for someone who has neither.
    """
    title = "Import players from CSV"
    columns = imports.PLAYER_COLUMNS
    example = "name,rating\nAlice Chen,1350\nBen Ortiz,"
    notes = (
        "rating is optional and defaults to 1200. It seeds the starting "
        "rating; match results are what change it afterwards. A player who "
        "is already on the roster is skipped, never overwritten, and the "
        "comparison ignores capitalisation."
    )

    def build(self, rows):
        return imports.build_players(rows)

    def write(self, to_create):
        imports.save_players(to_create)

class ImportMatchesView(CsvImportView):
    """
        Bulk match upload, for backfilling a season or a tournament that was
        recorded on paper.

        Ratings are rebuilt once after the insert rather than per match, so
        the file does not need to be in chronological order and a large
        import costs one replay instead of one per row. See
        imports.save_matches.
    """
    title = "Import matches from CSV"
    columns = imports.MATCH_COLUMNS
    example = (
        "player1,player2,score1,score2,date\n"
        "Alice Chen,Ben Ortiz,11,7,2026-08-20 19:30"
    )
    notes = (
        "player1 and player2 must already be on the roster; a name that is "
        "not there is skipped rather than created. A date without a UTC "
        "offset is read in the timezone named in the page footer, so it "
        "means the same time it would mean on the match form. Ratings are "
        "rebuilt once after the import, so the file does not need to be in "
        "date order."
    )

    def build(self, rows):
        return imports.build_matches(rows)

    def write(self, to_create):
        imports.save_matches(to_create)
