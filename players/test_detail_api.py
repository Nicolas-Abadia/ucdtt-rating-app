from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Match, Player


@override_settings(SECURE_SSL_REDIRECT=False)
class PlayerProfileTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.a = Player.objects.create(name="Alice")
        self.b = Player.objects.create(name="Ben")
        self.c = Player.objects.create(name="Carla")
        self.day = timezone.now() - timedelta(days=2)

    def profile(self, player):
        response = self.client.get(f"/api/players/{player.pk}/profile/")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_totals_count_matches_in_both_slots(self):
        # Alice wins as player1, then loses as player2.
        Match.objects.create(player1=self.a, player2=self.b,
            score1=11, score2=7, date=self.day)
        Match.objects.create(player1=self.c, player2=self.a,
            score1=11, score2=9, date=self.day + timedelta(minutes=1))
        payload = self.profile(self.a)
        self.assertEqual(payload["total_matches"], 2)
        self.assertEqual(payload["wins"], 1)
        self.assertEqual(payload["losses"], 1)
        self.assertEqual(payload["win_percentage"], 50.0)

    def test_rank_matches_leaderboard_competition_ranking(self):
        Player.objects.filter(pk__in=[self.a.pk, self.b.pk]).update(rating=1500)
        Player.objects.filter(pk=self.c.pk).update(rating=1400)
        self.assertEqual(self.profile(self.a)["rank"], 1)
        # Equal rating shares the same rank, like the leaderboard.
        self.assertEqual(self.profile(self.b)["rank"], 1)
        self.assertEqual(self.profile(self.c)["rank"], 3)

    def test_player_without_matches(self):
        payload = self.profile(self.a)
        self.assertEqual(payload["total_matches"], 0)
        self.assertIsNone(payload["win_percentage"])
        self.assertEqual(payload["rating_history"], [])
        self.assertEqual(payload["display_rating"], self.a.initial_rating)
        self.assertEqual(payload["highest_rating"], self.a.initial_rating)

    def test_rating_history_is_limited_to_ninety_days(self):
        old = Match.objects.create(player1=self.a, player2=self.b,
            score1=11, score2=7, date=timezone.now() - timedelta(days=100))
        recent = Match.objects.create(player1=self.a, player2=self.b,
            score1=11, score2=7, date=self.day)
        payload = self.profile(self.a)
        self.assertEqual([point["match"] for point in payload["rating_history"]], [recent.pk])
        self.assertNotIn(old.pk, [point["match"] for point in payload["rating_history"]])
        self.assertTrue(payload["history_complete"])
        # Chronological order within the window.
        another = Match.objects.create(player1=self.b, player2=self.a,
            score1=11, score2=7, date=self.day + timedelta(minutes=1))
        payload = self.profile(self.a)
        self.assertEqual([point["match"] for point in payload["rating_history"]],
            [recent.pk, another.pk])

    def test_payload_includes_identity_fields(self):
        payload = self.profile(self.a)
        for key in ("id", "name", "style", "grip", "created_date",
                    "display_rating", "initial_rating", "rank",
                    "history_start", "history_end"):
            self.assertIn(key, payload)

    def test_unknown_player_returns_404(self):
        self.assertEqual(self.client.get("/api/players/99999/profile/").status_code, 404)


@override_settings(SECURE_SSL_REDIRECT=False)
class PlayerMatchesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.a = Player.objects.create(name="Alice")
        self.b = Player.objects.create(name="Ben")
        self.c = Player.objects.create(name="Carla")
        self.day = timezone.now() - timedelta(days=2)

    def matches(self, player, **params):
        response = self.client.get(f"/api/players/{player.pk}/matches/", params)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_scoped_to_exact_participant_in_either_slot(self):
        first = Match.objects.create(player1=self.a, player2=self.b,
            score1=11, score2=7, date=self.day)
        second = Match.objects.create(player1=self.c, player2=self.a,
            score1=9, score2=11, date=self.day + timedelta(minutes=1))
        Match.objects.create(player1=self.b, player2=self.c,
            score1=11, score2=5, date=self.day + timedelta(minutes=2))
        payload = self.matches(self.a)
        self.assertEqual(payload["count"], 2)
        # Newest first, card representation included.
        self.assertEqual([row["id"] for row in payload["results"]], [second.pk, first.pk])
        self.assertIn("player1_rating", payload["results"][0])

    def test_paginates_with_existing_paginator(self):
        for index in range(21):
            Match.objects.create(player1=self.a, player2=self.b, score1=11, score2=8,
                date=self.day + timedelta(minutes=index))
        first_page = self.matches(self.a)
        self.assertEqual(first_page["count"], 21)
        self.assertEqual(len(first_page["results"]), 20)
        self.assertIsNotNone(first_page["next"])
        self.assertEqual(len(self.matches(self.a, page=2)["results"]), 1)

    def test_unknown_player_returns_404(self):
        self.assertEqual(self.client.get("/api/players/99999/matches/").status_code, 404)


@override_settings(SECURE_SSL_REDIRECT=False)
class HeadToHeadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.a = Player.objects.create(name="Alice")
        self.b = Player.objects.create(name="Ben")
        self.c = Player.objects.create(name="Carla")
        self.day = timezone.now() - timedelta(days=2)

    def head_to_head(self, match, **params):
        response = self.client.get(f"/api/matches/{match.pk}/head-to-head/", params)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_record_counts_both_orientations(self):
        # Alice beats Ben as player1, Ben beats Alice as player1, then Alice
        # wins again. The record is the pair's global tally, including the
        # selected match itself.
        Match.objects.create(player1=self.a, player2=self.b,
            score1=11, score2=7, date=self.day)
        Match.objects.create(player1=self.b, player2=self.a,
            score1=11, score2=9, date=self.day + timedelta(minutes=1))
        current = Match.objects.create(player1=self.a, player2=self.b,
            score1=11, score2=3, date=self.day + timedelta(minutes=2))
        payload = self.head_to_head(current)
        self.assertEqual(payload["record"], {"player1_wins": 2, "player2_wins": 1})
        self.assertEqual(payload["count"], 3)

    def test_counts_current_and_future_meetings_excluding_unrelated(self):
        # Three meetings share a timestamp and fall back to the primary-key
        # tiebreak; only the Alice-Ben pair counts, not Alice-Carla. The
        # scores differ because the model rejects byte-identical duplicates.
        earlier_same_time = Match.objects.create(player1=self.b, player2=self.a,
            score1=11, score2=5, date=self.day)
        current = Match.objects.create(player1=self.a, player2=self.b,
            score1=11, score2=7, date=self.day)
        later_same_time = Match.objects.create(player1=self.b, player2=self.a,
            score1=11, score2=6, date=self.day)
        future = Match.objects.create(player1=self.a, player2=self.b,
            score1=11, score2=7, date=self.day + timedelta(days=1))
        Match.objects.create(player1=self.a, player2=self.c,
            score1=11, score2=7, date=self.day - timedelta(days=1))
        payload = self.head_to_head(current)
        self.assertEqual(payload["count"], 4)
        self.assertEqual([row["id"] for row in payload["results"]],
            [future.pk, later_same_time.pk, current.pk, earlier_same_time.pk])
        # Alice (player1 on the selected match) won the selected and future
        # meetings; Ben won the two meetings where he was player1.
        self.assertEqual(payload["record"], {"player1_wins": 2, "player2_wins": 2})

    def test_results_are_cards_and_paginated(self):
        for index in range(21):
            Match.objects.create(player1=self.a, player2=self.b, score1=11, score2=8,
                date=self.day + timedelta(minutes=index))
        current = Match.objects.create(player1=self.a, player2=self.b,
            score1=11, score2=8, date=self.day + timedelta(minutes=21))
        first_page = self.head_to_head(current)
        self.assertEqual(first_page["count"], 22)
        self.assertEqual(len(first_page["results"]), 20)
        # The record counts every meeting, including the selected match, not
        # just the first page.
        self.assertEqual(first_page["record"], {"player1_wins": 22, "player2_wins": 0})
        self.assertIn("player1_rating", first_page["results"][0])
        self.assertEqual(len(self.head_to_head(current, page=2)["results"]), 2)

    def test_unknown_match_returns_404_and_anonymous_writes_are_rejected(self):
        self.assertEqual(self.client.get("/api/matches/99999/head-to-head/").status_code, 404)
        match = Match.objects.create(player1=self.a, player2=self.b,
            score1=11, score2=7, date=self.day)
        # The action is GET-only, and unauthenticated requests meet the auth
        # gate first: 401, not a written row.
        self.assertEqual(
            self.client.post(f"/api/matches/{match.pk}/head-to-head/", {}).status_code, 401)


@override_settings(SECURE_SSL_REDIRECT=False)
class MatchDetailCardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.a = Player.objects.create(name="Alice")
        self.b = Player.objects.create(name="Ben")
        self.match = Match.objects.create(player1=self.a, player2=self.b,
            score1=11, score2=7, date=timezone.now() - timedelta(days=1))

    def test_include_card_retrieve_returns_card_fields_and_rating_changes(self):
        response = self.client.get(f"/api/matches/{self.match.pk}/?include=card")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("player1_rating", payload)
        self.assertIn("player2_rating", payload)
        self.assertIn("rating_changes", payload)
        self.assertEqual(payload["player1_rating"]["rating_after"], 1216)

    def test_plain_retrieve_contract_is_preserved(self):
        response = self.client.get(f"/api/matches/{self.match.pk}/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertNotIn("player1_rating", payload)
        self.assertIn("rating_changes", payload)
