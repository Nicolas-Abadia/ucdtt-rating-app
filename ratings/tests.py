import unittest
from ratings.elo import expected_score, rating_update


class EloMathTests(unittest.TestCase):
    def test_equal_ratings_expected_score_is_half(self):
        """
        When both players have the same rating, each has a 50% expected score.
        """
        self.assertEqual(expected_score(1500, 1500), 0.5)

    def test_equal_ratings_winner_gains_sixteen(self):
        """
        Two 1500 players, winner gets 16 points, loser loses 16.
        K=32, so the move is K/2 for a 0.5-vs-0.5 expected score.
        """
        new_a, new_b = rating_update(1500, 1500, 1)
        self.assertEqual(new_a, 1516)
        self.assertEqual(new_b, 1484)

    def test_heavy_favorite_winning_gains_little(self):
        """
        A 400-point favorite winning should barely move.
        """
        new_a, new_b = rating_update(1800, 1400, 1)
        self.assertEqual(new_a, 1803)
        self.assertEqual(new_b, 1397)

    def test_upset_moves_ratings_a_lot(self):
        """
        A 400-point underdog winning should move both ratings substantially.
        """
        new_a, new_b = rating_update(1400, 1800, 1)
        self.assertEqual(new_a, 1429)
        self.assertEqual(new_b, 1771)

    def test_rating_sum_is_conserved(self):
        """
        The total rating across both players must stay the same after a match.
        This guards against rounding drift.
        """
        cases = [
            (1500, 1500, 1),
            (1500, 1500, 0),
            (1800, 1400, 1),
            (1800, 1400, 0),
            (1400, 1800, 1),
            (1400, 1800, 0),
        ]
        for a, b, score in cases:
            new_a, new_b = rating_update(a, b, score)
            self.assertEqual(a + b, new_a + new_b)

    def test_both_players_use_pre_match_ratings(self):
        """
        The pure function must not mutate its inputs and must compute both
        new ratings from the original pair.
        """
        a, b = 1500, 1500
        new_a, new_b = rating_update(a, b, 1)
        # original values unchanged
        self.assertEqual(a, 1500)
        self.assertEqual(b, 1500)
        # result is computed from the original pair, not from an already-updated one
        self.assertEqual(new_a, 1516)
        self.assertEqual(new_b, 1484)
