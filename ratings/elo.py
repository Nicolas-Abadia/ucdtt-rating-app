def expected_score(rating_a, rating_b):
    """
    Player A's expected score against B: their win probability, derived
    from the rating difference alone.
    """
    return 1 / (1 + 10 ** ((rating_b - rating_a)/400))

def rating_update(rating_a, rating_b, score_a, k=32):
    """
    Returns (new_rating_a, new_rating_b) as floats.

    score_a is 1 for a win and 0 for a loss.

    Ratings are stored unrounded and rounded only for display, by
    Player.display_rating.
    """
    expected_a = expected_score(rating_a, rating_b)
    delta = k * (score_a - expected_a)
    return rating_a + delta, rating_b - delta
