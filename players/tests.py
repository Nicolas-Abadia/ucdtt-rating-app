from django.test import TestCase
from .models import Player
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
