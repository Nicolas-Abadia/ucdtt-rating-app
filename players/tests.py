from django.test import TestCase
import datetime
from django.contrib.auth.models import User
from django.utils import formats, timezone
from .models import Player, Match, RatingHistory
from django.urls import reverse
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO
import os
import tempfile

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
        # giving the wrong numbers (1198/1202).
        self.assertEqual(p1.rating, 1201)
        self.assertEqual(p2.rating, 1199)

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
        self.assertEqual(p1.rating, 1199)
        self.assertEqual(p2.rating, 1201)
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
        self.assertEqual(self.p1.rating, 1199)
        self.assertEqual(self.p2.rating, 1201)

        # Move the second match to before the first one.
        later.date = timezone.make_aware(datetime.datetime(2026, 8, 5, 0, 0, 0))
        later.save()

        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.rating, 1201)
        self.assertEqual(self.p2.rating, 1199)
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
        # to the two starting ratings.
        self.assertEqual(p1.rating + p2.rating, 1300 + 1200)

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
