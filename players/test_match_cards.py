from datetime import datetime, timedelta, timezone as dt_timezone

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from .match_cards import with_match_card_ratings
from .models import Match, Player, RatingHistory
from .serializers import MatchCardSerializer


@override_settings(SECURE_SSL_REDIRECT=False)
class MatchCardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.a = Player.objects.create(name="Alice")
        self.b = Player.objects.create(name="Ben")
        self.c = Player.objects.create(name="Carla")
        self.day = timezone.now() - timedelta(days=2)
        self.first = Match.objects.create(player1=self.a, player2=self.b,
            score1=11, score2=7, date=self.day)
        self.second = Match.objects.create(player1=self.c, player2=self.a,
            score1=9, score2=11, date=self.day + timedelta(minutes=1))

    def cards(self, **params):
        response = self.client.get('/api/matches/', {'include': 'card', **params})
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_first_match_starts_from_initial_rating(self):
        row = self.cards(match_id=self.first.pk)['results'][0]
        self.assertEqual(row['player1_name'], 'Alice')
        self.assertEqual(row['player2_name'], 'Ben')
        self.assertEqual(row['player1_rating'], {
            'rating_before': 1200, 'rating_after': 1216, 'change': 16, 'direction': 'up'})
        self.assertEqual(row['player2_rating']['change'], -16)
        self.assertNotIn('rating_changes', row)

    def test_uses_previous_match_not_current_player_rating(self):
        row = self.cards(match_id=self.second.pk)['results'][0]
        self.assertEqual(row['player2_rating']['rating_before'], 1216)
        before = self.cards(match_id=self.first.pk)['results'][0]
        self.assertEqual(before['player1_rating']['rating_after'], 1216)

    def test_same_timestamp_uses_match_primary_key(self):
        third = Match.objects.create(player1=self.a, player2=self.b,
            score1=8, score2=11, date=self.second.date)
        rows = self.cards()['results']
        self.assertEqual([row['id'] for row in rows], [third.pk, self.second.pk, self.first.pk])
        self.assertEqual(rows[0]['player1_rating']['rating_before'], rows[1]['player2_rating']['rating_after'])

    def test_card_serialization_does_not_add_per_match_queries(self):
        request = APIRequestFactory().get('/api/matches/')
        with self.assertNumQueries(1):
            data = MatchCardSerializer(with_match_card_ratings(Match.objects.all()),
                many=True, context={'request': request}).data
            self.assertEqual(len(data), 2)

    def test_default_list_and_detail_contracts_are_preserved(self):
        row = self.client.get('/api/matches/').json()['results'][0]
        self.assertEqual(set(row), {'id', 'url', 'player1', 'player2', 'score1', 'score2', 'date'})
        detail = self.client.get(f'/api/matches/{self.first.pk}/?include=card').json()
        self.assertIn('rating_changes', detail)
        embedded = self.client.get(f'/api/players/{self.a.pk}/').json()['matches']
        self.assertTrue(all('rating_changes' not in row and 'player1_rating' not in row for row in embedded))

    def test_search_and_exact_match_id(self):
        self.assertEqual(self.cards(q='car')['count'], 1)
        self.assertEqual(self.cards(q=str(self.a.pk))['count'], 2)
        self.assertEqual(self.cards(match_id=self.first.pk, q='Carla')['count'], 0)
        for value in ['invalid', '-1', '0', '999999999999999999999999', '1.5']:
            with self.subTest(value=value):
                self.assertEqual(self.cards(match_id=value)['count'], 0)
        for value in ['9' * 5000, '²']:
            with self.subTest(query=value):
                self.assertEqual(self.cards(q=value)['count'], 0)

    def test_missing_history_is_explicit_not_fabricated(self):
        RatingHistory.objects.filter(match=self.first, player=self.a).delete()
        row = self.cards(match_id=self.first.pk)['results'][0]
        self.assertIsNone(row['player1_rating'])
        next_row = self.cards(match_id=self.second.pk)['results'][0]
        self.assertIsNone(next_row['player2_rating'])

    def test_replay_after_edit_updates_card(self):
        self.first.score1, self.first.score2 = 7, 11
        self.first.save()
        row = self.cards(match_id=self.first.pk)['results'][0]
        self.assertEqual(row['player1_rating']['change'], -16)
        next_row = self.cards(match_id=self.second.pk)['results'][0]
        self.assertEqual(next_row['player2_rating']['rating_before'], 1184)

    def test_backdated_insert_and_delete_reconcile_card_history(self):
        earlier = Match.objects.create(player1=self.a, player2=self.c,
            score1=11, score2=4, date=self.day - timedelta(minutes=1))
        row = self.cards(match_id=self.first.pk)['results'][0]
        self.assertEqual(row['player1_rating']['rating_before'], 1216)
        earlier.delete()
        row = self.cards(match_id=self.first.pk)['results'][0]
        self.assertEqual(row['player1_rating']['rating_before'], 1200)

    def test_pagination_retains_card_representation(self):
        for index in range(20):
            Match.objects.create(player1=self.a, player2=self.b, score1=11, score2=8,
                date=self.day + timedelta(minutes=index + 2))
        first_page = self.cards()
        self.assertEqual(first_page['count'], 22)
        self.assertEqual(len(first_page['results']), 20)
        self.assertIn('include=card', first_page['next'])
        self.assertEqual(len(self.cards(page=2)['results']), 2)
        # Searching is applied before pagination: matches normally on page 2
        # must still be returned on the first page of their filtered results.
        self.assertNotIn(self.first.pk, [row['id'] for row in first_page['results']])
        self.assertEqual([row['id'] for row in self.cards(match_id=self.first.pk)['results']], [self.first.pk])
        self.assertEqual([row['id'] for row in self.cards(q='Carla')['results']], [self.second.pk])

    def test_endpoint_stays_read_only(self):
        self.assertEqual(self.client.post('/api/matches/?include=card', {}).status_code, 405)

    def test_date_filter_matches_the_device_calendar_day(self):
        self.first.date = datetime(2026, 8, 1, 2, 30, tzinfo=dt_timezone.utc)
        self.first.save()
        self.assertEqual(self.cards(match_id=self.first.pk, date='2026-07-31', tz='America/Sao_Paulo')['count'], 1)
        self.assertEqual(self.cards(match_id=self.first.pk, date='2026-08-01', tz='America/Sao_Paulo')['count'], 0)
        self.assertEqual(self.cards(q='Alice', date='2026-07-31', tz='America/Sao_Paulo')['count'], 1)
        # No tz parameter: the day boundary follows the browser's tz cookie,
        # which TimezoneMiddleware activates for the request (a bare
        # timezone.override would be reset to settings.TIME_ZONE instead).
        self.client.cookies.load({'tz': 'UTC'})
        self.assertEqual(self.cards(match_id=self.first.pk, date='2026-08-01')['count'], 1)
        self.assertEqual(self.cards(match_id=self.first.pk, date='2026-07-31')['count'], 0)

    def test_date_filter_handles_daylight_saving_boundaries(self):
        # March 8 in Los Angeles is a 23-hour day in 2026.
        instants = [(8, 7, 59), (8, 8, 0), (9, 6, 59), (9, 7, 0)]
        matches = [Match.objects.create(player1=self.a, player2=self.b, score1=11, score2=5,
            date=datetime(2026, 3, day, hour, minute, tzinfo=dt_timezone.utc))
            for day, hour, minute in instants]
        rows = self.cards(date='2026-03-08', tz='America/Los_Angeles')['results']
        self.assertEqual([row['id'] for row in rows], [matches[2].pk, matches[1].pk])

    def test_invalid_filter_timezone_returns_validation_error(self):
        response = self.client.get('/api/matches/', {'date': '2026-08-01', 'tz': 'Not/AZone'})
        self.assertEqual(response.status_code, 400)

    def test_empty_list(self):
        Match.objects.all().delete()
        self.assertEqual(self.cards()['results'], [])
