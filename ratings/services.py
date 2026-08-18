from django.db import transaction

from ratings.elo import rating_update
from players.models import Player, Match, RatingHistory

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

    # Log history (single round trip for both rows)
    RatingHistory.objects.bulk_create(
        [
            RatingHistory(player=match.player1, match=match, rating=new_r1),
            RatingHistory(player=match.player2, match=match, rating=new_r2),
        ]
    )


def recompute_all_ratings():
    """
    Resets every player to their initial rating, clears rating history, and
    replays all matches in chronological (date, id) order to rebuild
    ratings and history from scratch.

    Used by the `recompute_ratings` management command, and automatically
    by Match.save() (players/models.py) whenever a match is created with a
    date earlier than an existing match, since a single incremental update
    would otherwise apply the wrong pre-match ratings.

    Returns the number of matches replayed.
    """
    with transaction.atomic():
        for player in Player.objects.all():
            player.rating = player.initial_rating
            player.save()

        RatingHistory.objects.all().delete()

        # NOTE: intentionally not select_related. Each iteration must read
        # player1/player2's *current* rating, including the update just
        # written by the previous iteration. select_related would join all
        # rows against a single upfront snapshot of the player table,
        # taken before any replay writes happened, which silently breaks
        # the sequential (Elo depends on prior state) replay.
        matches = Match.objects.order_by("date", "id")
        count = 0
        for match in matches:
            update_ratings_from_match(match)
            count += 1

    return count