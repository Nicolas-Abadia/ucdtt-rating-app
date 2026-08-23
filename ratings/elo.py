def expected_score(rating_a, rating_b):
    """
    Player A's expected score against B: their win probability, derived
    from the rating difference alone.
    """
    return 1 / (1 + 10 ** ((rating_b - rating_a)/400))

def rating_update(rating_a, rating_b, score_a, k=32):
    """
        Returns (new_rating_a, new_rating_b) as floats.
        score_a: 1 for win, 0 for loss, 0.5 for draw.

        The result is deliberately not rounded. The update is
        k * (score - expected), and because the expected score is the win
        probability, the probability-weighted rating change of any match is
        exactly zero for both players. That is the property that makes the
        system unexploitable: no choice of opponent is better than another.

        Rounding each delta to a whole number broke it. Past a gap of
        400 * log10(63) ~= 720 points a favorite's win was worth
        round(0.499) = 0, while an upset still cost the full 32, so playing a
        much weaker opponent carried an expected value of -0.5 points per
        match. Strong players could only lose ground by facing weaker ones,
        which is the opposite of what the club wants to encourage.

        A guaranteed minimum gain of 1 would fix that symptom and introduce a
        worse problem: at the same gap it makes the expected value +0.49 per
        match, so repeatedly beating the weakest available opponent becomes
        the fastest way up the leaderboard. Letting sub-point gains
        accumulate is the honest version of the same idea.

        Ratings are stored unrounded and rounded only for display, via
        Player.display_rating.
    """
    expected_a = expected_score(rating_a, rating_b)
    delta = k * (score_a - expected_a)
    return rating_a + delta, rating_b - delta
