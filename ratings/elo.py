def expected_score(rating_a, rating_b):
    
    return 1 / (1 + 10 ** ((rating_b - rating_a)/400))

def rating_update(rating_a, rating_b, score_a, k=32):
    """
        Returns (new_rating_a, new_rating_b) as integers.
        score_a: 1 for win, 0 for loss, 0.5 for draw.
    """
    expected_a = expected_score(rating_a, rating_b)
    new_a = rating_a + k * (score_a - expected_a)
    new_b = rating_b - k * (score_a - expected_a)
    return round(new_a), round(new_b)