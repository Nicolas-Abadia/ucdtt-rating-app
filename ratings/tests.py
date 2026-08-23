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
        self.assertAlmostEqual(new_a, 1802.9091, places=4)
        self.assertAlmostEqual(new_b, 1397.0909, places=4)

    def test_upset_moves_ratings_a_lot(self):
        """
        A 400-point underdog winning should move both ratings substantially.
        """
        new_a, new_b = rating_update(1400, 1800, 1)
        self.assertAlmostEqual(new_a, 1429.0909, places=4)
        self.assertAlmostEqual(new_b, 1770.9091, places=4)

    def test_rating_sum_is_conserved(self):
        """
        The total rating across both players must stay the same after a
        match: one player's gain is exactly the other's loss.

        assertAlmostEqual rather than assertEqual because the deltas are
        floats. (a + delta) + (b - delta) equals a + b in real arithmetic but
        not necessarily in IEEE 754, which can differ in the last bits.
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
            self.assertAlmostEqual(a + b, new_a + new_b, places=6)

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

    def test_favorite_past_the_old_rounding_cliff_still_gains(self):
        """
        720 points is the gap where round(delta) used to reach zero, so a
        favorite gained nothing for a win while an upset still cost the full
        32. The gain must be positive, and smaller than a single point.
        """
        new_a, new_b = rating_update(1920, 1200, 1)
        self.assertGreater(new_a, 1920)
        self.assertLess(new_a - 1920, 1)
        self.assertAlmostEqual(new_a, 1920.4993, places=4)
        self.assertAlmostEqual(new_b, 1199.5007, places=4)

    def test_two_wins_at_a_large_gap_move_the_whole_number_rating(self):
        """
        The reason ratings are stored unrounded: sub-point gains accumulate.
        Two wins at a 720-point gap are worth about half a point each, so the
        rating a member sees moves after the second win, not the first.
        """
        rating_a, rating_b = 1920, 1200

        rating_a, rating_b = rating_update(rating_a, rating_b, 1)
        self.assertEqual(round(rating_a), 1920)

        rating_a, rating_b = rating_update(rating_a, rating_b, 1)
        self.assertEqual(round(rating_a), 1921)

    def test_expected_rating_change_is_zero(self):
        """
        Elo's central property, and the reason a guaranteed minimum gain was
        rejected: because the expected score is the win probability, the
        probability-weighted rating change of a match is zero. No opponent is
        a better choice than any other.
        """
        for rating_a, rating_b in [(1200, 1200), (1920, 1200), (1400, 1800)]:
            p_win = expected_score(rating_a, rating_b)
            gain = rating_update(rating_a, rating_b, 1)[0] - rating_a
            loss = rating_update(rating_a, rating_b, 0)[0] - rating_a
            self.assertAlmostEqual(
                p_win * gain + (1 - p_win) * loss, 0, places=6
            )
