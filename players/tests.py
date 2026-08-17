from django.test import TestCase
import datetime
from django.utils import formats, timezone
from .models import Player, Match
from django.urls import reverse

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