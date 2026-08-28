from django.test import TestCase
import datetime
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import formats, timezone
from .models import Player, Match, RatingHistory
from django.urls import reverse
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO
import os
import tempfile
from zoneinfo import ZoneInfo

# Create your tests here.


class PlayerIndexViewTests(TestCase):
    def test_list_all_players(self):
        """
        All players are displayed on the index page in correct order.
        """
        player1 = Player.objects.create(name="Player01", rating=1300)
        player2 = Player.objects.create(name="Player02", rating=1900)

        response = self.client.get(reverse("players:index"))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["player_list"], [player2, player1])

    def test_list_no_players(self):
        """
        No players are displayed if no players exist in db.
        """
        response = self.client.get(reverse("players:index"))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["player_list"], [])

class PlayerDetailViewTests(TestCase):
    def test_detail(self):
        """
        Check if the detail page shows the correct info for a player
        """
        
        player1 = Player.objects.create(name="player1", rating="2340")
        url = reverse("players:detail", args=(player1.id,))
        response = self.client.get(url)

        # Get the current active timezone (the one the template is using)
        current_tz = timezone.get_current_timezone()
        # Shift the database datetime to match that timezone explicitly
        localized_date = player1.created_date.astimezone(current_tz)

        # Check correct status code
        self.assertEqual(response.status_code, 200)
        # Check if player object is waiting to be used by the template
        self.assertEqual(response.context["player"], player1)
        # Check if the particular attributes match inside the context
        self.assertEqual(response.context["player"].name, player1.name)
        self.assertEqual(response.context["player"].rating, int(player1.rating))
        self.assertEqual(response.context["player"].created_date, player1.created_date)
        # Check if response body contains the object's attributes
        self.assertContains(response, player1.name)
        self.assertContains(response, player1.rating)
        self.assertContains(response, formats.date_format(localized_date, "DATETIME_FORMAT"))

class AddPlayerViewTests(TestCase):
    def setUp(self):
        self.officer = User.objects.create_user(username="officer", password="testpass123")
        self.client.login(username="officer", password="testpass123")

    def test_form_loads(self):
        response = self.client.get(reverse("players:new"))
        self.assertEqual(response.status_code, 200)
    def test_create_player(self):
        response = self.client.post(
            reverse("players:new"),
            {"name": "Player A", "initial_rating": 1200},
        )
        self.assertRedirects(response, reverse("players:index"))
        self.assertEqual(Player.objects.count(), 1)
        player = Player.objects.first()
        self.assertEqual(player.name, "Player A")
        self.assertEqual(player.rating, 1200)
    def test_invalid_renders_form(self):
        response = self.client.post(
            reverse("players:new"),
            {"name": "", "initial_rating": 1200},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Player.objects.count(), 0)


class EditPlayerViewTests(TestCase):
    def setUp(self):
        self.officer = User.objects.create_user(username="officer", password="testpass123")
        self.client.login(username="officer", password="testpass123")

    def test_form_load(self):
        player = Player.objects.create(name="PlayerA", rating=1200)
        response = self.client.get(reverse("players:update", args=(player.id,)))
        self.assertEqual(response.status_code, 200)
    def test_update_player(self):
        player = Player.objects.create(name="PlayerA", rating=1405, initial_rating=1405)
        response = self.client.post(
            reverse("players:update", args=(player.id,)),
            {"name": "PlayerA updated", "initial_rating": 1300}
        )
        self.assertRedirects(response, reverse("players:index"))
        player.refresh_from_db()
        self.assertEqual(player.name, "PlayerA updated")
        self.assertEqual(player.initial_rating, 1300)
        # This player has no matches, so replaying from the new starting
        # point leaves the current rating equal to it.
        self.assertEqual(player.rating, 1300)

    def test_invalid_renders_form(self):
        player = Player.objects.create(name="Player A", rating=1200)
        response = self.client.post(
            reverse("players:update", args=(player.id,)),
            {"name": "", "initial_rating": 1300},
        )
        self.assertEqual(response.status_code, 200)
        player.refresh_from_db()
        self.assertEqual(player.name, "Player A")

class DeletePlayerViewTests(TestCase):
    def setUp(self):
        self.officer = User.objects.create_user(username="officer", password="testpass123")
        self.client.login(username="officer", password="testpass123")

    def test_delete_confirmation(self):
        player = Player.objects.create(name="Player A", rating=1200)
        response = self.client.get(reverse("players:delete", args=(player.id,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Player A")
    def test_delete_player(self):
        player = Player.objects.create(name="Player A", rating=1200)
        response = self.client.post(
            reverse("players:delete", args=(player.id,)),
        )
        self.assertRedirects(response, reverse("players:index"))
        self.assertEqual(Player.objects.count(), 0)


class MatchListViewTests(TestCase):
    def match_date(self):
        return timezone.make_aware(datetime.datetime(2026, 8, 16, 0, 0, 0))

    def test_no_matches(self):
        response = self.client.get(reverse("players:matches"))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["match_list"], [])
    def test_matches_listed(self):
        p1 = Player.objects.create(name="Player A", rating=1200)
        p2 = Player.objects.create(name="Player B", rating=1200)
        match = Match.objects.create(player1=p1, player2=p2, score1=11, score2=4, date=self.match_date())
        response = self.client.get(reverse("players:matches"))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["match_list"], [match])
        self.assertContains(response, "Player A")
        self.assertContains(response, "11-4")


class LogMatchViewTests(TestCase):
    def setUp(self):
        self.officer = User.objects.create_user(username="officer", password="testpass123")
        self.client.login(username="officer", password="testpass123")

    def test_form_loads(self):
        response = self.client.get(reverse("players:new_match"))
        self.assertEqual(response.status_code, 200)
    def test_create_match(self):
        p1 = Player.objects.create(name="Player A", rating=1200)
        p2 = Player.objects.create(name="Player B", rating=1200)
        response = self.client.post(
            reverse("players:new_match"),
            {
                "player1": p1.id,
                "player2": p2.id,
                "score1": 11,
                "score2": 9,
                "date": "2026-08-16",
            },
        )
        self.assertRedirects(response, reverse("players:matches"))
        self.assertEqual(Match.objects.count(), 1)
    def test_invalid_renders_form(self):
        p1 = Player.objects.create(name="Player A", rating=1200)
        response = self.client.post(
            reverse("players:new_match"),
            {
                "player1": p1.id,
                "player2": "",
                "score1": 11,
                "score2": 9,
                "date": "2026-08-16",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Match.objects.count(), 0)


class RatingUpdateTests(TestCase):
    def setUp(self):
        self.officer = User.objects.create_user(username="officer", password="testpass123")
        self.client.login(username="officer", password="testpass123")

    def test_log_match_updates_player_ratings(self):
        p1 = Player.objects.create(name="Player A", rating=1200)
        p2 = Player.objects.create(name="Player B", rating=1200)
        self.client.post(
            reverse("players:new_match"),
            {
                "player1": p1.id,
                "player2": p2.id,
                "score1": 11,
                "score2": 9,
                "date": "2026-08-16",
            },
        )
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertEqual(p1.rating, 1216)
        self.assertEqual(p2.rating, 1184)
        self.assertEqual(p1.initial_rating, 1200)
        self.assertEqual(p2.initial_rating, 1200)


class AddPlayerInitialRatingTests(TestCase):
    def setUp(self):
        self.officer = User.objects.create_user(username="officer", password="testpass123")
        self.client.login(username="officer", password="testpass123")

    def test_add_player_sets_initial_rating(self):
        self.client.post(
            reverse("players:new"),
            {"name": "Player A", "initial_rating": 1300},
        )
        player = Player.objects.first()
        self.assertEqual(player.rating, 1300)
        self.assertEqual(player.initial_rating, 1300)


class RecomputeRatingsCommandTests(TestCase):
    def setUp(self):
        self.officer = User.objects.create_user(username="officer", password="testpass123")
        self.client.login(username="officer", password="testpass123")

    def test_recompute_restores_ratings_from_history(self):
        p1 = Player.objects.create(name="Player A", rating=1200)
        p2 = Player.objects.create(name="Player B", rating=1200)
        self.client.post(
            reverse("players:new_match"),
            {
                "player1": p1.id,
                "player2": p2.id,
                "score1": 11,
                "score2": 9,
                "date": "2026-08-16",
            },
        )
        # Mess up ratings manually
        p1.rating = 999
        p2.rating = 1000
        p1.save()
        p2.save()

        out = StringIO()
        call_command("recompute_ratings", stdout=out)

        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertEqual(p1.rating, 1216)
        self.assertEqual(p2.rating, 1184)
        self.assertIn("Recomputed ratings for 1 match(es)", out.getvalue())


class OutOfOrderMatchTests(TestCase):
    def test_backdated_match_triggers_full_recompute(self):
        """
        Creating a match dated before an already-existing match must not
        apply that match's rating change on top of today's (already
        updated) ratings. It should instead trigger a full recompute so
        every match is replayed in chronological order.
        """
        p1 = Player.objects.create(name="Player A", rating=1200)
        p2 = Player.objects.create(name="Player B", rating=1200)

        # Log the later match first (normal, in-order creation).
        Match.objects.create(
            player1=p1,
            player2=p2,
            score1=11,
            score2=9,
            date=timezone.make_aware(datetime.datetime(2026, 8, 16, 0, 0, 0)),
        )
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertEqual(p1.rating, 1216)
        self.assertEqual(p2.rating, 1184)

        # Now backdate a second match to before the first one.
        Match.objects.create(
            player1=p1,
            player2=p2,
            score1=9,
            score2=11,
            date=timezone.make_aware(datetime.datetime(2026, 8, 10, 0, 0, 0)),
        )
        p1.refresh_from_db()
        p2.refresh_from_db()

        # Correct chronological replay: the 08-10 match (p1 loses) is
        # applied first from the initial 1200/1200 ratings, then the
        # 08-16 match (p1 wins) is applied on top of that result. A naive
        # incremental update (the bug) would instead apply the 08-10
        # match's result on top of the already-updated 1216/1184 ratings,
        # landing on 1198.53/1201.47, i.e. the two players the wrong way
        # round.
        #
        # Ratings are stored as floats, so these are the exact replay
        # values rather than the 1201/1199 they are displayed as.
        self.assertAlmostEqual(p1.rating, 1201.4695, places=4)
        self.assertAlmostEqual(p2.rating, 1198.5305, places=4)
        self.assertEqual(p1.display_rating, 1201)
        self.assertEqual(p2.display_rating, 1199)

        # Recompute clears and rebuilds history from scratch: 2 matches,
        # 2 rating rows each.
        self.assertEqual(RatingHistory.objects.count(), 4)

    def test_matches_created_in_order_are_not_recomputed(self):
        """
        Sanity check: creating matches in chronological order should not
        be treated as out-of-order, and should keep working as a plain
        incremental update.
        """
        p1 = Player.objects.create(name="Player A", rating=1200)
        p2 = Player.objects.create(name="Player B", rating=1200)

        Match.objects.create(
            player1=p1,
            player2=p2,
            score1=11,
            score2=9,
            date=timezone.make_aware(datetime.datetime(2026, 8, 10, 0, 0, 0)),
        )
        Match.objects.create(
            player1=p1,
            player2=p2,
            score1=9,
            score2=11,
            date=timezone.make_aware(datetime.datetime(2026, 8, 16, 0, 0, 0)),
        )

        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertAlmostEqual(p1.rating, 1198.5305, places=4)
        self.assertAlmostEqual(p2.rating, 1201.4695, places=4)
        self.assertEqual(RatingHistory.objects.count(), 4)


class MatchEditAndDeleteRatingTests(TestCase):
    """
    Ratings are derived from the match records, so editing or deleting a
    match has to be reflected in them. Creation is covered by
    OutOfOrderMatchTests; these cover edits and deletions.
    """

    def setUp(self):
        self.p1 = Player.objects.create(name="Player A", rating=1200)
        self.p2 = Player.objects.create(name="Player B", rating=1200)

    def make_match(self, score1, score2, day):
        return Match.objects.create(
            player1=self.p1,
            player2=self.p2,
            score1=score1,
            score2=score2,
            date=timezone.make_aware(datetime.datetime(2026, 8, day, 0, 0, 0)),
        )

    def test_editing_match_score_recomputes_ratings(self):
        """
        Correcting a mis-entered score has to move the ratings that were
        computed from the wrong score.
        """
        match = self.make_match(11, 9, 16)
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.rating, 1216)
        self.assertEqual(self.p2.rating, 1184)

        # The score was entered backwards: Player B actually won.
        match.score1 = 9
        match.score2 = 11
        match.save()

        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.rating, 1184)
        self.assertEqual(self.p2.rating, 1216)
        # History was rebuilt, not appended to: still one match, two rows.
        self.assertEqual(RatingHistory.objects.count(), 2)

    def test_editing_match_date_replays_in_the_new_order(self):
        """
        Changing a match's date can reorder the replay, which changes the
        pre-match ratings every later match was computed from.
        """
        self.make_match(11, 9, 10)  # Player A wins, earlier
        later = self.make_match(9, 11, 16)  # Player B wins, later

        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertAlmostEqual(self.p1.rating, 1198.5305, places=4)
        self.assertAlmostEqual(self.p2.rating, 1201.4695, places=4)

        # Move the second match to before the first one.
        later.date = timezone.make_aware(datetime.datetime(2026, 8, 5, 0, 0, 0))
        later.save()

        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertAlmostEqual(self.p1.rating, 1201.4695, places=4)
        self.assertAlmostEqual(self.p2.rating, 1198.5305, places=4)
        self.assertEqual(RatingHistory.objects.count(), 4)

    def test_deleting_only_match_restores_initial_ratings(self):
        """
        Deleting a match must not raise (its history rows cascade) and must
        leave both players back at their initial ratings.
        """
        match = self.make_match(11, 9, 16)
        match.delete()

        self.assertEqual(Match.objects.count(), 0)
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.rating, 1200)
        self.assertEqual(self.p2.rating, 1200)
        self.assertEqual(RatingHistory.objects.count(), 0)

    def test_deleting_one_of_two_matches_keeps_the_other(self):
        """
        Only the deleted match's effect disappears; the remaining match is
        replayed from the initial ratings.
        """
        self.make_match(11, 9, 10)
        second = self.make_match(9, 11, 16)
        second.delete()

        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.rating, 1216)
        self.assertEqual(self.p2.rating, 1184)
        self.assertEqual(RatingHistory.objects.count(), 2)


class DeletePlayerWithMatchesTests(TestCase):
    def setUp(self):
        self.officer = User.objects.create_user(username="officer", password="testpass123")
        self.client.login(username="officer", password="testpass123")
        self.p1 = Player.objects.create(name="Player A", rating=1200)
        self.p2 = Player.objects.create(name="Player B", rating=1200)
        Match.objects.create(
            player1=self.p1,
            player2=self.p2,
            score1=11,
            score2=9,
            date=timezone.make_aware(datetime.datetime(2026, 8, 16, 0, 0, 0)),
        )

    def test_delete_is_refused_with_a_message(self):
        """
        A player with recorded matches is PROTECTed. The refusal should be
        reported to the officer, not raised as a 500.
        """
        response = self.client.post(
            reverse("players:delete", args=(self.p1.id,)), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "recorded matches")
        self.assertEqual(Player.objects.count(), 2)
        self.assertEqual(Match.objects.count(), 1)


class MatchAdminValidationTests(TestCase):
    """
    MatchAdmin uses MatchForm, so the admin enforces the same rules as the
    officer-facing form instead of only the database constraints.
    """

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin", password="testpass123", email="admin@example.com"
        )
        self.client.login(username="admin", password="testpass123")
        self.p1 = Player.objects.create(name="Player A", rating=1200)
        self.p2 = Player.objects.create(name="Player B", rating=1200)

    def test_admin_rejects_tied_match(self):
        response = self.client.post(
            reverse("admin:players_match_add"),
            {
                "player1": self.p1.id,
                "player2": self.p2.id,
                "score1": 11,
                "score2": 11,
                "date": "2026-08-16",
            },
        )
        # Re-renders the form with errors instead of redirecting.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Match.objects.count(), 0)

    def test_admin_accepts_valid_match_and_updates_ratings(self):
        response = self.client.post(
            reverse("admin:players_match_add"),
            {
                "player1": self.p1.id,
                "player2": self.p2.id,
                "score1": 11,
                "score2": 9,
                "date": "2026-08-16",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Match.objects.count(), 1)
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.rating, 1216)
        self.assertEqual(self.p2.rating, 1184)


class EditPlayerInitialRatingTests(TestCase):
    def setUp(self):
        self.officer = User.objects.create_user(username="officer", password="testpass123")
        self.client.login(username="officer", password="testpass123")

    def test_changing_initial_rating_replays_matches_from_it(self):
        """
        initial_rating seeds the replay, so changing it has to move the
        current rating too rather than waiting for an unrelated recompute.

        The exact Elo arithmetic is covered by EloMathTests; this asserts
        the replay actually restarted from the new seed.
        """
        p1 = Player.objects.create(name="Player A", rating=1200, initial_rating=1200)
        p2 = Player.objects.create(name="Player B", rating=1200, initial_rating=1200)
        Match.objects.create(
            player1=p1,
            player2=p2,
            score1=11,
            score2=9,
            date=timezone.make_aware(datetime.datetime(2026, 8, 16, 0, 0, 0)),
        )
        p1.refresh_from_db()
        self.assertEqual(p1.rating, 1216)

        response = self.client.post(
            reverse("players:update", args=(p1.id,)),
            {"name": "Player A", "initial_rating": 1300},
        )
        self.assertRedirects(response, reverse("players:index"))

        p1.refresh_from_db()
        p2.refresh_from_db()
        # Replayed from 1300 instead of 1200, so no longer the old 1216.
        self.assertNotEqual(p1.rating, 1216)
        # Player A still won that match, so they are above their new seed.
        self.assertGreater(p1.rating, 1300)
        # Elo moves points between the two players, so the pair still sums
        # to the two starting ratings. Compared with a tolerance because
        # (a + delta) + (b - delta) is not exactly a + b in IEEE 754.
        self.assertAlmostEqual(p1.rating + p2.rating, 1300 + 1200, places=6)

    def test_editing_only_the_name_leaves_ratings_alone(self):
        """
        A name change is not a rating change, so it must not disturb a
        rating that the matches produced.
        """
        p1 = Player.objects.create(name="Player A", rating=1200, initial_rating=1200)
        p2 = Player.objects.create(name="Player B", rating=1200, initial_rating=1200)
        Match.objects.create(
            player1=p1,
            player2=p2,
            score1=11,
            score2=9,
            date=timezone.make_aware(datetime.datetime(2026, 8, 16, 0, 0, 0)),
        )

        self.client.post(
            reverse("players:update", args=(p1.id,)),
            {"name": "Player A renamed", "initial_rating": 1200},
        )

        p1.refresh_from_db()
        self.assertEqual(p1.name, "Player A renamed")
        self.assertEqual(p1.rating, 1216)


class OfficerSignUpFeedbackTests(TestCase):
    """
    A successful signup redirects to the leaderboard, which says nothing
    about the account that was just created, and officers are auth users
    rather than players, so they show up in no list either. The message is
    the only confirmation the officer gets, which is why it is asserted on.
    """

    def setUp(self):
        User.objects.create_user(username="officer", password="testpass123")
        self.client.login(username="officer", password="testpass123")

    def test_created_officer_is_reported_on_the_landing_page(self):
        response = self.client.post(
            reverse("players:signup"),
            {
                "username": "newofficer",
                "password1": "str0ng-testpass!",
                "password2": "str0ng-testpass!",
            },
            follow=True,
        )
        self.assertRedirects(response, reverse("players:index"))
        self.assertTrue(User.objects.filter(username="newofficer").exists())
        # The username, not the whole sentence: the quotes around it are
        # HTML-escaped in the rendered page.
        self.assertContains(response, "newofficer")
        self.assertContains(response, "created")

    def test_rejected_signup_reports_nothing(self):
        """
        No account, no success message. A message queued before validation
        would announce a signup that never happened.
        """
        response = self.client.post(
            reverse("players:signup"),
            {
                "username": "newofficer",
                "password1": "str0ng-testpass!",
                "password2": "different-testpass!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newofficer").exists())
        self.assertEqual(list(response.context["messages"]), [])


class OfficerOnlyVisibilityTests(TestCase):
    """
    These actions are already blocked by LoginRequiredMixin. What's checked
    here is that they aren't advertised to visitors who can't use them, so
    the templates' {% if user.is_authenticated %} guards can't be dropped
    without a test noticing.

    Each assertion targets the action's URL rather than its button label or
    HTML tag. A label or tag can change for purely cosmetic reasons, which
    makes the negative assertions pass even with the guard removed. The URL
    is what actually leaks, so it is what gets asserted on.
    """

    def setUp(self):
        self.player = Player.objects.create(name="Player A", rating=1200)

    def login_as_officer(self):
        User.objects.create_user(username="officer", password="testpass123")
        self.client.login(username="officer", password="testpass123")

    def edit_url(self):
        return reverse("players:update", args=(self.player.id,))

    def delete_url(self):
        return reverse("players:delete", args=(self.player.id,))

    def test_detail_hides_edit_and_delete_from_visitors(self):
        response = self.client.get(reverse("players:detail", args=(self.player.id,)))
        self.assertNotContains(response, self.edit_url())
        self.assertNotContains(response, self.delete_url())

    def test_detail_shows_edit_and_delete_to_officers(self):
        self.login_as_officer()
        response = self.client.get(reverse("players:detail", args=(self.player.id,)))
        self.assertContains(response, self.edit_url())
        self.assertContains(response, self.delete_url())

    def test_index_hides_add_player_from_visitors(self):
        response = self.client.get(reverse("players:index"))
        self.assertNotContains(response, reverse("players:new"))

    def test_index_shows_add_player_to_officers(self):
        self.login_as_officer()
        response = self.client.get(reverse("players:index"))
        self.assertContains(response, reverse("players:new"))

    def test_match_list_hides_add_match_from_visitors(self):
        response = self.client.get(reverse("players:matches"))
        self.assertNotContains(response, reverse("players:new_match"))

    def test_match_list_shows_add_match_to_officers(self):
        self.login_as_officer()
        response = self.client.get(reverse("players:matches"))
        self.assertContains(response, reverse("players:new_match"))


class DeleteMatchViewTests(TestCase):
    def setUp(self):
        self.p1 = Player.objects.create(name="Player A", rating=1200, initial_rating=1200)
        self.p2 = Player.objects.create(name="Player B", rating=1200, initial_rating=1200)
        self.match = Match.objects.create(
            player1=self.p1,
            player2=self.p2,
            score1=11,
            score2=9,
            date=timezone.make_aware(datetime.datetime(2026, 8, 16, 0, 0, 0)),
        )

    def login_as_officer(self):
        User.objects.create_user(username="officer", password="testpass123")
        self.client.login(username="officer", password="testpass123")

    def test_confirmation_page_loads_for_officers(self):
        self.login_as_officer()
        response = self.client.get(
            reverse("players:delete_match", args=(self.match.id,))
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Player A")

    def test_delete_match_recomputes_ratings(self):
        self.login_as_officer()
        response = self.client.post(
            reverse("players:delete_match", args=(self.match.id,))
        )
        self.assertRedirects(response, reverse("players:matches"))
        self.assertEqual(Match.objects.count(), 0)

        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.rating, 1200)
        self.assertEqual(self.p2.rating, 1200)
        self.assertEqual(RatingHistory.objects.count(), 0)

    def test_visitors_cannot_delete_a_match(self):
        """
        Deleting a match rewrites everyone's ratings, so it must be
        officer-only at the view level and not just hidden in the template.
        """
        response = self.client.post(
            reverse("players:delete_match", args=(self.match.id,))
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
        self.assertEqual(Match.objects.count(), 1)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.rating, 1216)

    def test_detail_page_shows_delete_only_to_officers(self):
        """
        The control lives on the match detail page, not on every row of the
        match list.
        """
        url = reverse("players:match_detail", args=(self.match.id,))
        response = self.client.get(url)
        self.assertNotContains(response, ">delete</button>")

        self.login_as_officer()
        response = self.client.get(url)
        self.assertContains(response, ">delete</button>")


class EditMatchViewTests(TestCase):
    """
    Correcting a mis-entered score is the most likely fix an officer needs.
    The rating replay itself is covered by MatchEditAndDeleteRatingTests;
    these cover the view, its validation, and its access control.
    """

    def setUp(self):
        self.p1 = Player.objects.create(name="Player A", rating=1200, initial_rating=1200)
        self.p2 = Player.objects.create(name="Player B", rating=1200, initial_rating=1200)
        self.match = Match.objects.create(
            player1=self.p1,
            player2=self.p2,
            score1=11,
            score2=9,
            date=timezone.make_aware(datetime.datetime(2026, 8, 16, 0, 0, 0)),
        )

    def login_as_officer(self):
        User.objects.create_user(username="officer", password="testpass123")
        self.client.login(username="officer", password="testpass123")

    def edit_url(self):
        return reverse("players:update_match", args=(self.match.id,))

    def test_form_loads_with_the_existing_match(self):
        self.login_as_officer()
        response = self.client.get(self.edit_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit match")
        # The date must come back in the datetime-local format the widget
        # expects, or the field renders blank and the officer has to retype
        # a date they never meant to change.
        self.assertContains(response, "2026-08-16T00:00")

    def test_correcting_a_reversed_score_fixes_the_ratings(self):
        self.login_as_officer()
        response = self.client.post(
            self.edit_url(),
            {
                "player1": self.p1.id,
                "player2": self.p2.id,
                "score1": 9,
                "score2": 11,
                "date": "2026-08-16",
            },
        )
        self.assertRedirects(response, reverse("players:matches"))

        self.match.refresh_from_db()
        self.assertEqual(self.match.score1, 9)
        self.assertEqual(self.match.score2, 11)

        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.rating, 1184)
        self.assertEqual(self.p2.rating, 1216)
        # Rebuilt, not appended to: still one match worth of history.
        self.assertEqual(RatingHistory.objects.count(), 2)

    def test_invalid_edit_is_rejected_and_changes_nothing(self):
        """
        An edit goes through the same MatchForm as a new match, so a tie is
        refused here too instead of only at the database constraint.
        """
        self.login_as_officer()
        response = self.client.post(
            self.edit_url(),
            {
                "player1": self.p1.id,
                "player2": self.p2.id,
                "score1": 11,
                "score2": 11,
                "date": "2026-08-16",
            },
        )
        self.assertEqual(response.status_code, 200)

        self.match.refresh_from_db()
        self.assertEqual(self.match.score1, 11)
        self.assertEqual(self.match.score2, 9)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.rating, 1216)

    def test_visitors_cannot_edit_a_match(self):
        response = self.client.post(
            self.edit_url(),
            {
                "player1": self.p1.id,
                "player2": self.p2.id,
                "score1": 9,
                "score2": 11,
                "date": "2026-08-16",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

        self.match.refresh_from_db()
        self.assertEqual(self.match.score1, 11)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.rating, 1216)

    def test_detail_page_shows_edit_only_to_officers(self):
        # Asserts on the edit URL rather than the button markup, so a
        # restyled template can't make this pass with the guard removed.
        url = reverse("players:match_detail", args=(self.match.id,))
        response = self.client.get(url)
        self.assertNotContains(response, self.edit_url())

        self.login_as_officer()
        response = self.client.get(url)
        self.assertContains(response, self.edit_url())


class MatchDetailViewTests(TestCase):
    def setUp(self):
        self.p1 = Player.objects.create(name="Player A", rating=1200, initial_rating=1200)
        self.p2 = Player.objects.create(name="Player B", rating=1200, initial_rating=1200)
        self.match = Match.objects.create(
            player1=self.p1,
            player2=self.p2,
            score1=11,
            score2=4,
            date=timezone.make_aware(datetime.datetime(2026, 8, 16, 0, 0, 0)),
        )

    def test_detail_shows_the_match(self):
        response = self.client.get(
            reverse("players:match_detail", args=(self.match.id,))
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Player A")
        self.assertContains(response, "Player B")
        self.assertContains(response, "11-4")

    def test_detail_links_to_both_players(self):
        response = self.client.get(
            reverse("players:match_detail", args=(self.match.id,))
        )
        self.assertContains(response, reverse("players:detail", args=(self.p1.id,)))
        self.assertContains(response, reverse("players:detail", args=(self.p2.id,)))

    def test_match_list_links_to_the_detail_page(self):
        response = self.client.get(reverse("players:matches"))
        self.assertContains(
            response, reverse("players:match_detail", args=(self.match.id,))
        )

    def test_missing_match_is_a_404(self):
        response = self.client.get(
            reverse("players:match_detail", args=(self.match.id + 999,))
        )
        self.assertEqual(response.status_code, 404)


class ImportPlayersCommandTests(TestCase):
    def run_import(self, csv_text, *args):
        """
        Writes csv_text to a temp file, runs import_players on it, and returns
        the command's stdout.
        """
        with tempfile.NamedTemporaryFile(
            "w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        ) as fh:
            fh.write(csv_text)
            path = fh.name
        out = StringIO()
        try:
            call_command("import_players", path, *args, stdout=out)
        finally:
            os.unlink(path)
        return out.getvalue()

    def test_imports_names_with_the_default_rating(self):
        self.run_import("name\nAlice\nBob\n")
        self.assertEqual(Player.objects.count(), 2)
        alice = Player.objects.get(name="Alice")
        self.assertEqual(alice.rating, 1200)
        self.assertEqual(alice.initial_rating, 1200)

    def test_seeded_rating_also_sets_initial_rating(self):
        """
        A seeded rating has to land in initial_rating as well. If it only lands
        in rating, the next recompute_all_ratings() resets the player to 1200.
        """
        self.run_import("name,rating\nAlice,1450\n")
        alice = Player.objects.get(name="Alice")
        self.assertEqual(alice.rating, 1450)
        self.assertEqual(alice.initial_rating, 1450)

    def test_seeded_rating_survives_a_recompute(self):
        """
        The regression the initial_rating handling exists to prevent.
        """
        self.run_import("name,rating\nAlice,1450\nBob,1100\n")
        call_command("recompute_ratings", stdout=StringIO())
        self.assertEqual(Player.objects.get(name="Alice").rating, 1450)
        self.assertEqual(Player.objects.get(name="Bob").rating, 1100)

    def test_skips_a_name_already_in_the_database(self):
        Player.objects.create(name="Alice")
        output = self.run_import("name\nalice\nBob\n")
        self.assertEqual(Player.objects.count(), 2)
        self.assertIn("already in the database", output)

    def test_skips_a_duplicate_within_the_file(self):
        output = self.run_import("name\nAlice\nALICE\n")
        self.assertEqual(Player.objects.count(), 1)
        self.assertIn("duplicated within the file", output)

    def test_skips_a_non_numeric_rating(self):
        output = self.run_import("name,rating\nAlice,not-a-number\nBob,1300\n")
        self.assertEqual(Player.objects.count(), 1)
        self.assertIn("not a whole number", output)

    def test_skips_a_rating_below_the_minimum(self):
        output = self.run_import("name,rating\nAlice,50\n")
        self.assertEqual(Player.objects.count(), 0)
        self.assertIn("below the minimum", output)

    def test_skips_a_blank_name(self):
        output = self.run_import('name\n"   "\nBob\n')
        self.assertEqual(Player.objects.count(), 1)
        self.assertIn("blank name", output)

    def test_dry_run_writes_nothing(self):
        output = self.run_import("name\nAlice\nBob\n", "--dry-run")
        self.assertEqual(Player.objects.count(), 0)
        self.assertIn("Dry run", output)

    def test_strips_the_spreadsheet_byte_order_mark(self):
        self.run_import("\ufeffname\nAlice\n")
        self.assertTrue(Player.objects.filter(name="Alice").exists())

    def test_a_missing_name_column_is_an_error(self):
        with self.assertRaises(CommandError):
            self.run_import("player\nAlice\n")

    def test_a_header_with_no_data_rows_is_an_error(self):
        with self.assertRaises(CommandError):
            self.run_import("name\n")

    def test_a_missing_file_is_an_error(self):
        with self.assertRaises(CommandError):
            call_command(
                "import_players", "/nonexistent/roster.csv", stdout=StringIO()
            )


class LargeRatingGapTests(TestCase):
    """
    While ratings were integers, a favourite more than ~720 points ahead
    gained exactly 0 after rounding, so they could never move no matter how
    many matches they won. Storing the float keeps the fraction, so the
    displayed rating still climbs over a few wins.
    """

    def setUp(self):
        self.strong = Player.objects.create(
            name="Strong", rating=1920, initial_rating=1920
        )
        self.weak = Player.objects.create(
            name="Weak", rating=1200, initial_rating=1200
        )

    def make_match(self, day):
        return Match.objects.create(
            player1=self.strong,
            player2=self.weak,
            score1=11,
            score2=4,
            date=timezone.make_aware(datetime.datetime(2026, 8, day, 0, 0, 0)),
        )

    def test_favorite_gains_from_beating_a_much_weaker_player(self):
        self.make_match(10)
        self.strong.refresh_from_db()
        self.weak.refresh_from_db()

        # A 720-point gap is right at the old rounding cliff: the gain is
        # real but smaller than one whole point, so nothing visible moves
        # yet.
        self.assertGreater(self.strong.rating, 1920)
        self.assertLess(self.weak.rating, 1200)
        self.assertEqual(self.strong.display_rating, 1920)

    def test_two_wins_move_the_displayed_rating(self):
        self.make_match(10)
        self.make_match(11)
        self.strong.refresh_from_db()

        # Two sub-point gains add up to more than half a point, so the
        # rating members actually see finally changes. Under the old
        # integer rounding this stayed at 1920 forever.
        self.assertEqual(self.strong.display_rating, 1921)


class TimezoneMiddlewareTests(TestCase):
    """The viewer's own timezone governs display and naive form input.

    Stored values are always UTC. Before TimezoneMiddleware, the active zone
    was settings.TIME_ZONE for everyone, so every visitor read Davis time on
    the clock, and a naive "now" typed from anywhere east of Davis was parsed
    as Davis time, landed in the future, and was rejected by Match.clean().
    """

    SAO_PAULO = "America/Sao_Paulo"

    def setUp(self):
        self.p1 = Player.objects.create(name="P1")
        self.p2 = Player.objects.create(name="P2")
        User.objects.create_user(username="officer", password="testpass123")
        self.client.login(username="officer", password="testpass123")

    def make_match(self):
        # 02:30 UTC is 23:30 the previous day in Sao Paulo and 19:30 the
        # previous day in Los Angeles, so no two zones render it alike.
        return Match.objects.create(
            player1=self.p1,
            player2=self.p2,
            score1=11,
            score2=9,
            date=datetime.datetime(2026, 8, 20, 2, 30, tzinfo=datetime.timezone.utc),
        )

    def formatted_in(self, when, zone_name):
        return formats.date_format(
            when.astimezone(ZoneInfo(zone_name)), "DATETIME_FORMAT"
        )

    def local_now_string(self):
        return timezone.now().astimezone(ZoneInfo(self.SAO_PAULO)).strftime(
            "%Y-%m-%dT%H:%M"
        )

    def new_match_payload(self, date_string):
        return {
            "player1": self.p1.id,
            "player2": self.p2.id,
            "score1": 11,
            "score2": 9,
            "date": date_string,
        }

    def test_datetime_renders_in_the_reported_timezone(self):
        match = self.make_match()
        self.client.cookies["tz"] = self.SAO_PAULO

        response = self.client.get(
            reverse("players:match_detail", args=(match.id,))
        )

        self.assertContains(response, self.formatted_in(match.date, self.SAO_PAULO))
        self.assertNotContains(
            response,
            self.formatted_in(match.date, timezone.get_default_timezone_name()),
        )
        # The footer names the zone, so a viewer can tell which clock applies.
        self.assertContains(response, self.SAO_PAULO)

    def test_unknown_timezone_cookie_falls_back_to_the_default(self):
        match = self.make_match()
        # The cookie is client-supplied. An unusable value must degrade to the
        # project default, not raise ZoneInfoNotFoundError and 500 the page.
        self.client.cookies["tz"] = "Mars/Olympus_Mons"

        response = self.client.get(
            reverse("players:match_detail", args=(match.id,))
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            self.formatted_in(match.date, timezone.get_default_timezone_name()),
        )

    def test_no_cookie_uses_the_default_timezone(self):
        match = self.make_match()

        response = self.client.get(
            reverse("players:match_detail", args=(match.id,))
        )

        self.assertContains(
            response,
            self.formatted_in(match.date, timezone.get_default_timezone_name()),
        )

    def test_active_timezone_does_not_leak_into_the_next_request(self):
        self.client.cookies["tz"] = self.SAO_PAULO

        self.client.get(reverse("players:matches"))

        # The active zone is thread-local and gunicorn reuses threads, so a
        # request that does not report a zone must not inherit the last one.
        self.assertEqual(
            timezone.get_current_timezone_name(),
            timezone.get_default_timezone_name(),
        )

    def test_current_local_time_is_accepted_from_a_zone_ahead_of_the_default(self):
        self.client.cookies["tz"] = self.SAO_PAULO

        self.client.post(
            reverse("players:new_match"),
            self.new_match_payload(self.local_now_string()),
        )

        self.assertEqual(Match.objects.count(), 1)

    def test_the_same_local_time_is_rejected_without_the_cookie(self):
        # Documents the original bug: with no reported zone the value is read
        # as Davis time, which is hours ahead of the wall clock in Brazil.
        response = self.client.post(
            reverse("players:new_match"),
            self.new_match_payload(self.local_now_string()),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Match.objects.count(), 0)

    def test_percent_encoded_cookie_value_is_still_understood(self):
        match = self.make_match()
        # Django never percent-decodes cookie values, so a client that writes
        # the zone through encodeURIComponent sends it in this shape. Browsers
        # that already stored it that way must keep working.
        self.client.cookies["tz"] = "America%2FSao_Paulo"

        response = self.client.get(
            reverse("players:match_detail", args=(match.id,))
        )

        self.assertContains(
            response, self.formatted_in(match.date, self.SAO_PAULO)
        )


class AccountEditingTests(TestCase):
    """
    One account page changing the username, the password, or both.

    The password half is Django's PasswordChangeForm, so these tests cover the
    wiring around it rather than Django's own validation: optional password
    fields, the session surviving the change, and neither half being written
    when the other fails.
    """

    PASSWORD = "testpass123"
    NEW_PASSWORD = "b3tterpassw0rd!"

    def setUp(self):
        self.officer = User.objects.create_user(
            username="officer", password=self.PASSWORD
        )
        self.client.login(username="officer", password=self.PASSWORD)
        self.url = reverse("players:account")

    def payload(self, **overrides):
        """Username unchanged and no password change, unless overridden."""
        data = {
            "username": "officer",
            "old_password": "",
            "new_password1": "",
            "new_password2": "",
        }
        data.update(overrides)
        return data

    def test_username_alone_changes_without_touching_the_password(self):
        response = self.client.post(
            self.url, self.payload(username="newofficer")
        )

        self.assertRedirects(response, self.url)
        self.officer.refresh_from_db()
        self.assertEqual(self.officer.username, "newofficer")
        self.assertTrue(self.officer.check_password(self.PASSWORD))

    def test_password_alone_changes_and_keeps_the_session(self):
        response = self.client.post(
            self.url,
            self.payload(
                old_password=self.PASSWORD,
                new_password1=self.NEW_PASSWORD,
                new_password2=self.NEW_PASSWORD,
            ),
        )

        # assertRedirects follows the redirect, so a session dropped by the
        # password change would show up here as a second redirect to login.
        self.assertRedirects(response, self.url)
        self.officer.refresh_from_db()
        self.assertEqual(self.officer.username, "officer")
        self.assertTrue(self.officer.check_password(self.NEW_PASSWORD))
        self.assertEqual(self.client.get(reverse("players:new")).status_code, 200)

    def test_username_and_password_change_in_one_submit(self):
        response = self.client.post(
            self.url,
            self.payload(
                username="newofficer",
                old_password=self.PASSWORD,
                new_password1=self.NEW_PASSWORD,
                new_password2=self.NEW_PASSWORD,
            ),
        )

        self.assertRedirects(response, self.url)
        self.officer.refresh_from_db()
        self.assertEqual(self.officer.username, "newofficer")
        self.assertTrue(self.officer.check_password(self.NEW_PASSWORD))
        self.assertEqual(self.client.get(reverse("players:new")).status_code, 200)

    def test_duplicate_username_blocks_the_whole_submit(self):
        User.objects.create_user(username="taken", password=self.PASSWORD)

        response = self.client.post(
            self.url,
            self.payload(
                username="taken",
                old_password=self.PASSWORD,
                new_password1=self.NEW_PASSWORD,
                new_password2=self.NEW_PASSWORD,
            ),
        )

        # A re-rendered form, not the IntegrityError a bare save would raise,
        # and the password half that did validate is not written on its own.
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["username_form"],
            "username",
            "A user with that username already exists.",
        )
        self.officer.refresh_from_db()
        self.assertEqual(self.officer.username, "officer")
        self.assertTrue(self.officer.check_password(self.PASSWORD))

    def test_wrong_old_password_blocks_the_whole_submit(self):
        response = self.client.post(
            self.url,
            self.payload(
                username="newofficer",
                old_password="not-the-old-password",
                new_password1=self.NEW_PASSWORD,
                new_password2=self.NEW_PASSWORD,
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.officer.refresh_from_db()
        self.assertEqual(self.officer.username, "officer")
        self.assertTrue(self.officer.check_password(self.PASSWORD))

    def test_weak_password_is_rejected_by_the_validators(self):
        response = self.client.post(
            self.url,
            self.payload(
                old_password=self.PASSWORD,
                new_password1="abc",
                new_password2="abc",
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.officer.refresh_from_db()
        self.assertTrue(self.officer.check_password(self.PASSWORD))

    def test_the_page_edits_only_the_signed_in_account(self):
        other = User.objects.create_user(
            username="other", password=self.PASSWORD
        )

        self.client.post(
            self.url,
            self.payload(
                username="renamed",
                old_password=self.PASSWORD,
                new_password1=self.NEW_PASSWORD,
                new_password2=self.NEW_PASSWORD,
            ),
        )

        # The view takes no pk, so there is no way to aim it at someone else.
        other.refresh_from_db()
        self.assertEqual(other.username, "other")
        self.assertTrue(other.check_password(self.PASSWORD))

    def test_submitting_nothing_new_is_a_no_op(self):
        response = self.client.post(self.url, self.payload())

        self.assertRedirects(response, self.url)
        self.officer.refresh_from_db()
        self.assertEqual(self.officer.username, "officer")
        self.assertTrue(self.officer.check_password(self.PASSWORD))

    def test_account_page_requires_login(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_the_built_in_password_change_url_redirects_to_the_account_page(self):
        response = self.client.get("/accounts/password_change/")

        self.assertRedirects(response, self.url)


class CsvImportViewTests(TestCase):
    """
    The officer-facing CSV uploads.

    Row-level parsing and validation are shared with the management commands
    (players/imports.py), so these cover the upload surface: login, the
    single upload that previews and is then confirmed, the held file and its
    token, the skipped-row report, rejected files, and the single rating
    rebuild that follows a match import.
    """

    PASSWORD = "testpass123"

    def setUp(self):
        User.objects.create_user(username="officer", password=self.PASSWORD)
        self.client.login(username="officer", password=self.PASSWORD)
        self.players_url = reverse("players:import_players")
        self.matches_url = reverse("players:import_matches")

    def upload(self, content, name="roster.csv"):
        return SimpleUploadedFile(
            name, content.encode("utf-8"), content_type="text/csv"
        )

    def add_two_players(self):
        Player.objects.create(name="Alice", rating=1200, initial_rating=1200)
        Player.objects.create(name="Ben", rating=1200, initial_rating=1200)

    def preview(self, url, content, name="roster.csv"):
        """Step one: upload the file and get the preview back."""
        return self.client.post(
            url, {"csv_file": self.upload(content, name=name)}
        )

    def confirm(self, url, token):
        """Step two: no file, only the token of the held one."""
        return self.client.post(url, {"confirm": "1", "token": token})

    def import_file(self, url, content, name="roster.csv"):
        """The whole flow: one upload, then the confirmation."""
        previewed = self.preview(url, content, name=name)
        return self.confirm(url, previewed.context["token"])

    def test_player_import_requires_login(self):
        self.client.logout()

        response = self.client.get(self.players_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_match_import_requires_login(self):
        self.client.logout()

        response = self.client.get(self.matches_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_uploading_previews_and_writes_nothing(self):
        response = self.preview(self.players_url, "name,rating\nAlice,1300\n")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["pending"]), 1)
        self.assertTrue(response.context["token"])
        self.assertEqual(Player.objects.count(), 0)

    def test_confirming_needs_the_token_but_not_the_file_again(self):
        previewed = self.preview(self.players_url, "name,rating\nAlice,1300\n")

        # No csv_file in this request: the point of the whole change.
        response = self.confirm(self.players_url, previewed.context["token"])

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["imported"])
        self.assertEqual(Player.objects.count(), 1)

    def test_confirming_twice_imports_once(self):
        previewed = self.preview(self.players_url, "name,rating\nAlice,1300\n")
        token = previewed.context["token"]
        self.confirm(self.players_url, token)

        # A refresh or a second click on the same button. The token was
        # consumed by the first confirmation, so there is nothing to redo.
        response = self.confirm(self.players_url, token)

        self.assertTrue(response.context["expired"])
        self.assertEqual(Player.objects.count(), 1)

    def test_an_unknown_token_writes_nothing(self):
        response = self.confirm(self.players_url, "not-a-real-token")

        self.assertTrue(response.context["expired"])
        self.assertEqual(Player.objects.count(), 0)

    def test_discarding_a_preview_forgets_the_file(self):
        previewed = self.preview(self.players_url, "name,rating\nAlice,1300\n")
        token = previewed.context["token"]

        discarded = self.client.post(self.players_url, {"discard": "1"})
        response = self.confirm(self.players_url, token)

        self.assertRedirects(discarded, self.players_url)
        self.assertTrue(response.context["expired"])
        self.assertEqual(Player.objects.count(), 0)

    def test_a_roster_token_cannot_be_confirmed_by_the_match_importer(self):
        previewed = self.preview(self.players_url, "name,rating\nAlice,1300\n")

        response = self.confirm(
            self.matches_url, previewed.context["token"]
        )

        self.assertTrue(response.context["expired"])
        self.assertEqual(Player.objects.count(), 0)

    def test_the_confirmation_re_reads_the_database(self):
        previewed = self.preview(
            self.players_url, "name,rating\nAlice,1300\nBen,1250\n"
        )
        self.assertEqual(len(previewed.context["pending"]), 2)
        # Somebody adds Alice by hand between the preview and its
        # confirmation. The rows are validated again, so she is reported as
        # skipped rather than written twice.
        Player.objects.create(name="alice", rating=1200, initial_rating=1200)

        response = self.confirm(self.players_url, previewed.context["token"])

        self.assertEqual(len(response.context["created"]), 1)
        skipped = response.context["skipped"]
        self.assertEqual(len(skipped), 1)
        self.assertIn("already in the database", skipped[0][1])
        self.assertEqual(Player.objects.count(), 2)

    def test_a_file_with_no_importable_row_is_not_held(self):
        Player.objects.create(name="Alice", rating=1200, initial_rating=1200)

        response = self.preview(self.players_url, "name,rating\nAlice,1300\n")

        self.assertEqual(response.context["pending"], [])
        self.assertEqual(response.context["token"], "")
        self.assertEqual(len(response.context["skipped"]), 1)

    def test_import_creates_players(self):
        response = self.import_file(
            self.players_url, "name,rating\nAlice,1300\nBen,\n"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Player.objects.count(), 2)
        self.assertEqual(Player.objects.get(name="Alice").initial_rating, 1300)
        # A blank rating falls back to the default, in both columns, so a
        # later recompute cannot wipe it.
        ben = Player.objects.get(name="Ben")
        self.assertEqual(ben.initial_rating, 1200)
        self.assertEqual(ben.rating, 1200)

    def test_skipped_rows_are_reported_and_the_rest_still_imports(self):
        Player.objects.create(name="alice", rating=1200, initial_rating=1200)

        response = self.import_file(
            self.players_url, "name,rating\nAlice,1300\nBen,1250\n"
        )

        self.assertEqual(Player.objects.count(), 2)
        skipped = response.context["skipped"]
        self.assertEqual(len(skipped), 1)
        self.assertIn("already in the database", skipped[0][1])

    def test_a_missing_column_is_a_form_error_and_writes_nothing(self):
        response = self.client.post(
            self.players_url,
            {"csv_file": self.upload("player,rating\nAlice,1300\n")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "csv_file",
            "The CSV needs a 'name' column. Found: player, rating",
        )
        self.assertEqual(Player.objects.count(), 0)

    def test_a_file_that_is_not_a_csv_is_rejected(self):
        response = self.client.post(
            self.players_url,
            {"csv_file": self.upload("name\nAlice\n", name="roster.txt")},
        )

        self.assertFormError(
            response.context["form"], "csv_file", "That is not a .csv file."
        )
        self.assertEqual(Player.objects.count(), 0)

    def test_match_import_rebuilds_ratings_in_date_order(self):
        self.add_two_players()
        # Deliberately not in chronological order: the later match is listed
        # first. bulk_create bypasses Match.save(), so correctness here comes
        # entirely from the single recompute that follows, which replays in
        # (date, id) order.
        content = (
            "player1,player2,score1,score2,date\n"
            "Alice,Ben,11,7,2026-08-20 19:30\n"
            "Ben,Alice,11,9,2026-08-19 19:30\n"
        )

        response = self.import_file(
            self.matches_url, content, name="matches.csv"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Match.objects.count(), 2)
        # Ben wins on the 19th from 1200/1200, then Alice wins on the 20th
        # from 1184/1216. Applying them in file order would swap these.
        self.assertAlmostEqual(
            Player.objects.get(name="Alice").rating, 1201.4695008, places=4
        )
        self.assertAlmostEqual(
            Player.objects.get(name="Ben").rating, 1198.5304992, places=4
        )
        self.assertEqual(RatingHistory.objects.count(), 4)

    def test_match_rows_that_break_the_rules_are_skipped(self):
        self.add_two_players()
        future = (timezone.now() + datetime.timedelta(days=1)).strftime(
            "%Y-%m-%d %H:%M"
        )
        content = (
            "player1,player2,score1,score2,date\n"
            f"Alice,Ben,11,7,{future}\n"
            "Alice,Carla,11,7,2026-08-20 19:30\n"
            "Alice,Alice,11,7,2026-08-20 19:30\n"
            "Alice,Ben,11,11,2026-08-20 19:30\n"
            "Alice,Ben,11,7,sometime last week\n"
            "Alice,Ben,11,7,2026-08-20 19:30\n"
        )

        response = self.import_file(
            self.matches_url, content, name="matches.csv"
        )

        # Only the last row survives. Every rule that the database would
        # enforce is applied here instead, because one constraint violation
        # would roll back the whole import.
        self.assertEqual(Match.objects.count(), 1)
        reasons = [reason for line, reason in response.context["skipped"]]
        self.assertEqual(len(reasons), 5)
        self.assertIn("date is in the future", reasons[0])
        self.assertIn("not on the roster: Carla", reasons[1])
        self.assertIn("a player cannot play themselves", reasons[2])
        self.assertIn("one player must win", reasons[3])
        self.assertIn("date is not a date and time", reasons[4])

    def test_a_naive_date_is_read_in_the_viewers_timezone(self):
        self.add_two_players()
        self.client.cookies["tz"] = "America/Sao_Paulo"

        self.import_file(
            self.matches_url,
            "player1,player2,score1,score2,date\n"
            "Alice,Ben,11,7,2026-08-20 19:30\n",
            name="matches.csv",
        )

        # 19:30 in Sao Paulo (UTC-3) is 22:30 UTC. Storage is UTC either
        # way; the cookie is what decides which 19:30 was meant.
        stored = Match.objects.get().date.astimezone(datetime.timezone.utc)
        self.assertEqual(stored.strftime("%Y-%m-%d %H:%M"), "2026-08-20 22:30")


class ImportMatchesCommandTests(TestCase):
    """
    The match import command. Row validation is shared with the upload view,
    so this covers the command surface: file handling, the dry run, and the
    single rebuild reported at the end.
    """

    def setUp(self):
        self.alice = Player.objects.create(
            name="Alice", rating=1200, initial_rating=1200
        )
        self.ben = Player.objects.create(
            name="Ben", rating=1200, initial_rating=1200
        )

    def write_csv(self, content):
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".csv", delete=False, encoding="utf-8"
        )
        handle.write(content)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_imports_matches_and_rebuilds_ratings_once(self):
        path = self.write_csv(
            "player1,player2,score1,score2,date\n"
            "Alice,Ben,11,7,2026-08-20 19:30\n"
            "Ben,Alice,11,9,2026-08-19 19:30\n"
        )
        out = StringIO()

        call_command("import_matches", path, stdout=out)

        self.assertEqual(Match.objects.count(), 2)
        self.assertIn("Created 2 match(es)", out.getvalue())
        self.assertIn("Replayed 2 match(es)", out.getvalue())
        self.alice.refresh_from_db()
        self.assertAlmostEqual(self.alice.rating, 1201.4695008, places=4)

    def test_dry_run_writes_nothing(self):
        path = self.write_csv(
            "player1,player2,score1,score2,date\n"
            "Alice,Ben,11,7,2026-08-20 19:30\n"
        )
        out = StringIO()

        call_command("import_matches", path, "--dry-run", stdout=out)

        self.assertEqual(Match.objects.count(), 0)
        self.assertIn("Dry run: would create 1 match(es)", out.getvalue())
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.rating, 1200)

    def test_a_missing_column_is_reported(self):
        path = self.write_csv(
            "player1,player2,score1,date\nAlice,Ben,11,2026-08-20 19:30\n"
        )

        with self.assertRaisesMessage(
            CommandError, "The CSV needs a 'score2' column."
        ):
            call_command("import_matches", path, stdout=StringIO())

    def test_a_missing_file_is_reported(self):
        with self.assertRaisesMessage(CommandError, "No such file:"):
            call_command(
                "import_matches", "/nonexistent/matches.csv", stdout=StringIO()
            )
