from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from ratings.elo import rating_update

from .models import Match, Player


@override_settings(SECURE_SSL_REDIRECT=False)
class WritePermissionTests(TestCase):
    """Reads stay public; every write requires an authenticated officer."""

    def setUp(self):
        self.client = APIClient()
        self.a = Player.objects.create(name="Alice")
        self.b = Player.objects.create(name="Ben")
        self.match = Match.objects.create(player1=self.a, player2=self.b,
            score1=11, score2=7, date=timezone.now() - timedelta(days=1))

    def test_reads_stay_public(self):
        for url in ("/api/players/", f"/api/players/{self.a.pk}/",
                    f"/api/players/{self.a.pk}/profile/",
                    "/api/matches/", f"/api/matches/{self.match.pk}/",
                    f"/api/matches/{self.match.pk}/head-to-head/",
                    "/api/leaderboard/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_anonymous_writes_are_rejected(self):
        attempts = [
            ("post", "/api/players/", {"name": "Mallory"}),
            ("put", f"/api/players/{self.a.pk}/", {"name": "Alice"}),
            ("delete", f"/api/players/{self.a.pk}/", None),
            ("post", "/api/matches/", {"player1": self.a.pk, "player2": self.b.pk,
                                       "score1": 11, "score2": 5,
                                       "date": timezone.now().isoformat()}),
            ("put", f"/api/matches/{self.match.pk}/", {"player1": self.a.pk, "player2": self.b.pk,
                                                       "score1": 11, "score2": 9,
                                                       "date": self.match.date.isoformat()}),
            ("delete", f"/api/matches/{self.match.pk}/", None),
        ]
        for method, url, payload in attempts:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, payload, format="json")
                self.assertEqual(response.status_code, 401)
        self.assertEqual(Player.objects.count(), 2)
        self.assertEqual(Match.objects.count(), 1)


@override_settings(SECURE_SSL_REDIRECT=False)
class TokenBlacklistTests(TestCase):
    """Logout invalidates the refresh token server-side, not just locally."""

    def setUp(self):
        self.client = APIClient()
        User.objects.create_user("officer", password="testpass123")

    def test_blacklisted_refresh_token_cannot_mint_new_access(self):
        tokens = self.client.post("/api/token/", {
            "username": "officer", "password": "testpass123",
        }, format="json").json()
        response = self.client.post("/api/token/blacklist/",
            {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(response.status_code, 200)
        refresh = self.client.post("/api/token/refresh/",
            {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(refresh.status_code, 401)

    def test_valid_token_pair_still_refreshes(self):
        tokens = self.client.post("/api/token/", {
            "username": "officer", "password": "testpass123",
        }, format="json").json()
        refresh = self.client.post("/api/token/refresh/",
            {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(refresh.status_code, 200)
        self.assertIn("access", refresh.json())


@override_settings(SECURE_SSL_REDIRECT=False)
class PlayerWriteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(User.objects.create_user("officer"))
        self.a = Player.objects.create(name="Alice")
        self.b = Player.objects.create(name="Ben")

    def test_create_player_seeds_rating_from_initial(self):
        response = self.client.post("/api/players/", {
            "name": "Carla", "initial_rating": 1350,
            "style": "offensive", "grip": "shakehand",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        carla = Player.objects.get(name="Carla")
        self.assertEqual(carla.rating, 1350)
        self.assertEqual(carla.display_rating, 1350)

    def test_duplicate_name_is_a_field_error_not_a_500(self):
        response = self.client.post("/api/players/", {"name": "  alice  "}, format="json")
        self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/players/", {"name": "ALICE"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json())

    def test_edit_player_does_not_touch_rating_directly(self):
        response = self.client.patch(f"/api/players/{self.a.pk}/",
            {"style": "defensive"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.a.refresh_from_db()
        self.assertEqual(self.a.rating, 1200)

    def test_changing_initial_rating_recomputes(self):
        Match.objects.create(player1=self.a, player2=self.b,
            score1=11, score2=7, date=timezone.now() - timedelta(days=1))
        self.assertEqual(Player.objects.get(pk=self.a.pk).display_rating, 1216)
        response = self.client.patch(f"/api/players/{self.a.pk}/",
            {"initial_rating": 1500}, format="json")
        self.assertEqual(response.status_code, 200)
        # The replay reseeds Alice at 1500 before applying her win over Ben.
        expected_a, expected_b = rating_update(1500, 1200, 1)
        self.assertEqual(Player.objects.get(pk=self.a.pk).rating, expected_a)
        self.assertEqual(Player.objects.get(pk=self.b.pk).rating, expected_b)

    def test_delete_player_with_matches_is_refused_cleanly(self):
        Match.objects.create(player1=self.a, player2=self.b,
            score1=11, score2=7, date=timezone.now() - timedelta(days=1))
        response = self.client.delete(f"/api/players/{self.a.pk}/")
        self.assertEqual(response.status_code, 409)
        self.assertTrue(Player.objects.filter(pk=self.a.pk).exists())

    def test_delete_player_without_matches(self):
        response = self.client.delete(f"/api/players/{self.a.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Player.objects.filter(pk=self.a.pk).exists())


@override_settings(SECURE_SSL_REDIRECT=False)
class MatchWriteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(User.objects.create_user("officer"))
        self.a = Player.objects.create(name="Alice")
        self.b = Player.objects.create(name="Ben")
        self.c = Player.objects.create(name="Carla")
        self.day = timezone.now() - timedelta(days=1)

    def log(self, **overrides):
        payload = {"player1": self.a.pk, "player2": self.b.pk,
                   "score1": 11, "score2": 7, "date": self.day.isoformat()}
        payload.update(overrides)
        return self.client.post("/api/matches/", payload, format="json")

    def test_log_match_updates_ratings(self):
        response = self.log()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Player.objects.get(pk=self.a.pk).display_rating, 1216)
        self.assertEqual(Player.objects.get(pk=self.b.pk).display_rating, 1184)

    def test_validation_matches_the_html_form(self):
        cases = [
            ({"score2": 11}, "score2"),                      # tie
            ({"player2": self.a.pk}, "player2"),            # same player
            ({"date": (timezone.now() + timedelta(days=1)).isoformat()}, "date"),  # future
            ({"score1": -1}, "score1"),                      # negative score
        ]
        for overrides, field in cases:
            with self.subTest(overrides=overrides):
                response = self.log(**overrides)
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())
        self.assertEqual(Match.objects.count(), 0)

    def test_identical_duplicate_is_a_400(self):
        self.assertEqual(self.log().status_code, 201)
        response = self.log()
        self.assertEqual(response.status_code, 400)
        self.assertIn("non_field_errors", response.json())

    def test_edit_match_replays_every_rating(self):
        first = Match.objects.create(player1=self.a, player2=self.b,
            score1=11, score2=7, date=self.day)
        Match.objects.create(player1=self.c, player2=self.a,
            score1=9, score2=11, date=self.day + timedelta(minutes=1))
        response = self.client.put(f"/api/matches/{first.pk}/", {
            "player1": self.a.pk, "player2": self.b.pk,
            "score1": 7, "score2": 11, "date": first.date.isoformat(),
        }, format="json")
        self.assertEqual(response.status_code, 200)
        # The correction flips the first result (Alice 1200 -> 1184); the
        # second match was computed from the original, so the replay must
        # rebuild it from the corrected ratings.
        expected_c, expected_a = rating_update(1200, 1184, 0)
        self.assertEqual(Player.objects.get(pk=self.a.pk).rating, expected_a)
        self.assertEqual(Player.objects.get(pk=self.c.pk).rating, expected_c)

    def test_partial_edit_and_delete_recompute(self):
        match = Match.objects.create(player1=self.a, player2=self.b,
            score1=11, score2=7, date=self.day)
        response = self.client.patch(f"/api/matches/{match.pk}/",
            {"score1": 11, "score2": 9}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Player.objects.get(pk=self.a.pk).display_rating, 1216)
        response = self.client.delete(f"/api/matches/{match.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Player.objects.get(pk=self.a.pk).display_rating, 1200)
        self.assertEqual(Player.objects.get(pk=self.b.pk).display_rating, 1200)


@override_settings(SECURE_SSL_REDIRECT=False)
class CsvImportTests(TestCase):
    """The API import shares the HTML views' two-step preview-then-write."""

    def setUp(self):
        self.client = APIClient()
        self.officer = User.objects.create_user("officer")
        Player.objects.create(name="Alice")
        Player.objects.create(name="Ben")

    def upload(self, url, text, confirm=False):
        file = SimpleUploadedFile("roster.csv", text.encode("utf-8"),
                                  content_type="text/csv")
        suffix = "?confirm=1" if confirm else ""
        return self.client.post(f"{url}{suffix}", {"csv_file": file})

    def test_anonymous_import_is_rejected(self):
        response = self.upload("/api/players/import/", "name\nMallory\n")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Player.objects.count(), 2)

    def test_player_preview_writes_nothing(self):
        self.client.force_authenticate(self.officer)
        response = self.upload("/api/players/import/",
            "name,rating\nCarla,1350\nAlice,1400\n,1500\n")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["pending"], ["Carla (1350)"])
        self.assertEqual(len(payload["skipped"]), 2)
        self.assertEqual(Player.objects.count(), 2)

    def test_player_confirm_writes(self):
        self.client.force_authenticate(self.officer)
        response = self.upload("/api/players/import/", "name,rating\nCarla,1350\n", confirm=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["created"], ["Carla (1350)"])
        carla = Player.objects.get(name="Carla")
        self.assertEqual(carla.rating, 1350)
        self.assertEqual(carla.initial_rating, 1350)

    def test_unusable_file_is_a_400_field_error(self):
        self.client.force_authenticate(self.officer)
        response = self.upload("/api/players/import/", "rating\n1350\n")
        self.assertEqual(response.status_code, 400)
        self.assertIn("csv_file", response.json())

    def test_match_confirm_inserts_and_recomputes_once(self):
        self.client.force_authenticate(self.officer)
        yesterday = (timezone.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        response = self.upload("/api/matches/import/",
            f"player1,player2,score1,score2,date\nAlice,Ben,11,7,{yesterday}\n", confirm=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Match.objects.count(), 1)
        self.assertEqual(Player.objects.get(name="Alice").display_rating, 1216)
