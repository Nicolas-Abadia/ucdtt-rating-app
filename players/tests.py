from django.test import TestCase
import datetime
from django.contrib.auth.models import User
from django.utils import formats, timezone
from .models import Player, Match, RatingHistory
from django.urls import reverse
from django.core.management import call_command
from io import StringIO

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
            {"name": "Player A", "rating": 1200},
        )
        self.assertRedirects(response, reverse("players:index"))
        self.assertEqual(Player.objects.count(), 1)
        player = Player.objects.first()
        self.assertEqual(player.name, "Player A")
        self.assertEqual(player.rating, 1200)
    def test_invalid_renders_form(self):
        response = self.client.post(
            reverse("players:new"),
            {"name": "", "rating": 1200},
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
        player = Player.objects.create(name="PlayerA", rating=1405)
        response = self.client.post(
            reverse("players:update", args=(player.id,)),
            {"name":"PlayerA updated", "rating":1300}
        )
        self.assertRedirects(response, reverse("players:index"))
        player.refresh_from_db()
        self.assertEqual(player.name, "PlayerA updated")
        self.assertEqual(player.rating, 1300)

    def test_invalid_renders_form(self):
        player = Player.objects.create(name="Player A", rating=1200)
        response = self.client.post(
            reverse("players:update", args=(player.id,)),
            {"name": "", "rating": 1300},
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
            {"name": "Player A", "rating": 1300},
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
