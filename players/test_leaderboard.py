from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .leaderboard import leaderboard_queryset
from .models import Match, Player
from .serializers import LeaderboardSerializer


@override_settings(SECURE_SSL_REDIRECT=False)
class LeaderboardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.a = Player.objects.create(name="Alice")
        self.b = Player.objects.create(name="Ben")
        self.c = Player.objects.create(name="Carla")
        self.idle = Player.objects.create(name="Idle")
        now = timezone.now() - timedelta(days=1)
        self.m1 = Match.objects.create(player1=self.a, player2=self.b, score1=11, score2=7, date=now)
        self.m2 = Match.objects.create(player1=self.c, player2=self.a, score1=7, score2=11, date=now + timedelta(minutes=1))
        self.m3 = Match.objects.create(player1=self.a, player2=self.c, score1=8, score2=11, date=now + timedelta(minutes=2))
        self.m4 = Match.objects.create(player1=self.b, player2=self.a, score1=11, score2=9, date=now + timedelta(minutes=3))

    def board(self):
        response = self.client.get(reverse("leaderboard-list"))
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_counts_both_positions_without_join_multiplication(self):
        rows = {row["id"]: row for row in self.board()}
        for player, wins, losses in [(self.a, 2, 2), (self.b, 1, 1), (self.c, 1, 1), (self.idle, 0, 0)]:
            self.assertEqual((rows[player.pk]["wins"], rows[player.pk]["losses"]), (wins, losses))
        self.assertEqual(sum(row["wins"] for row in rows.values()), Match.objects.count())
        self.assertEqual(sum(row["losses"] for row in rows.values()), Match.objects.count())

    def test_only_six_fields_and_one_query_for_serialization(self):
        with self.assertNumQueries(1):
            rows = list(LeaderboardSerializer(leaderboard_queryset(), many=True).data)
        self.assertEqual(set(rows[0]), {"id", "name", "rank", "display_rating", "wins", "losses"})

    def test_full_roster_beyond_default_page_size(self):
        Player.objects.bulk_create([Player(name=f"Extra {i}") for i in range(25)])
        rows = self.board()
        self.assertEqual(len(rows), 29)
        general = self.client.get("/api/players/").json()
        self.assertEqual(general["count"], 29)
        self.assertEqual(len(general["results"]), 20)
        self.assertIsNotNone(general["next"])

    def test_exact_ratings_and_competition_ties(self):
        Player.objects.filter(pk__in=[self.a.pk, self.b.pk]).update(rating=1500.4)
        Player.objects.filter(pk=self.c.pk).update(rating=1500.1)
        Player.objects.filter(pk=self.idle.pk).update(rating=1200)
        rows = self.board()
        self.assertEqual([row["id"] for row in rows], [self.a.pk, self.b.pk, self.c.pk, self.idle.pk])
        self.assertEqual([row["rank"] for row in rows], [1, 1, 3, 4])
        self.assertEqual([row["display_rating"] for row in rows[:3]], [1500, 1500, 1500])

    def test_counts_change_after_edit_and_delete(self):
        self.m1.score1, self.m1.score2 = 7, 11
        self.m1.save()
        row = next(row for row in self.board() if row["id"] == self.a.pk)
        self.assertEqual((row["wins"], row["losses"]), (1, 3))
        self.m1.delete()
        row = next(row for row in self.board() if row["id"] == self.a.pk)
        self.assertEqual((row["wins"], row["losses"]), (1, 2))

    def test_empty_roster(self):
        Match.objects.all().delete()
        Player.objects.all().delete()
        self.assertEqual(self.board(), [])

    def test_leaderboard_is_read_only(self):
        self.assertEqual(self.client.post(reverse("leaderboard-list"), {}, format="json").status_code, 405)

    def test_embedded_match_summaries_do_not_repeat_rating_changes(self):
        data = self.client.get(f"/api/players/{self.a.pk}/").json()
        self.assertTrue(data["rating_history"])
        self.assertTrue(data["matches"])
        self.assertTrue(all("rating_changes" not in row for row in data["matches"]))

    def test_match_id_filter_is_exact_and_preserved(self):
        response = self.client.get(reverse("players:matches"), {"match_id": str(self.m2.pk)})
        self.assertEqual(list(response.context["match_list"]), [self.m2])
        self.assertEqual(response.context["match_id_filter"], str(self.m2.pk))
        self.assertContains(response, "Clear filters")
        self.assertContains(response, 'name="match_id"')
        self.assertContains(response, "margin-bottom: 1rem;")

    def test_match_id_composes_with_player_and_date_filters(self):
        params = {"match_id": self.m2.pk, "q": "Carla", "date": timezone.localtime(self.m2.date).date().isoformat()}
        response = self.client.get(reverse("players:matches"), params)
        self.assertEqual(list(response.context["match_list"]), [self.m2])
        params["q"] = "Ben"
        self.assertEqual(list(self.client.get(reverse("players:matches"), params).context["match_list"]), [])

    def test_bad_and_unknown_match_ids_return_no_matches(self):
        for value in ["abc", "-1", "0", "1.5", "999999999999999999999999", "9223372036854775808", "99999999"]:
            with self.subTest(value=value):
                response = self.client.get(reverse("players:matches"), {"match_id": value})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(list(response.context["match_list"]), [])

    def test_invalid_calendar_date_does_not_crash_match_filter(self):
        response = self.client.get(reverse("players:matches"), {"date": "2026-02-31"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["match_list"]), 4)
