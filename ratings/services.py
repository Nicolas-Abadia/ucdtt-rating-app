from ratings.elo import rating_update
from players.models import RatingHistory

STARTING_RATING = 1200

def score_from_match(player_score, opponent_score):
    if player_score > opponent_score:
        return 1
    if player_score < opponent_score:
        return 0
    return 0.5

def update_ratings_from_match(match):
    # Read pre-match ratings
    r1 = match.player1.rating
    r2 = match.player2.rating

    score_a = score_from_match(match.score1, match.score2)

    new_r1, new_r2 = rating_update(r1, r2, score_a)

    # Update players
    match.player1.rating = new_r1
    match.player2.rating = new_r2
    match.player1.save()
    match.player2.save()

    # Log history
    RatingHistory.objects.create(player=match.player1, match=match, rating=new_r1)
    RatingHistory.objects.create(player=match.player2, match=match, rating=new_r2)