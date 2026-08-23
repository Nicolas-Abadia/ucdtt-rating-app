from django.db import transaction

from ratings.elo import rating_update
from players.models import Player, Match, RatingHistory


def score_from_match(player_score, opponent_score):
    if player_score > opponent_score:
        return 1
    if player_score < opponent_score:
        return 0
    return 0.5


def _locked_players():
    """
    Reads every player, holding a row lock on each until the surrounding
    transaction ends. Returns {player_id: Player}.

    Rating computation is order-dependent: every result is calculated from
    the ratings the previous results produced, so two of them must never
    interleave. Without this, two officers submitting matches at the same
    moment would both read the same pre-match ratings and both write, and
    whichever committed second would silently discard the other's rating
    change while leaving its RatingHistory rows in place. No error, just
    wrong ratings.

    Every player is locked, not only the two in the match, because a full
    recompute touches everyone and has to be serialised against single-match
    updates as well. Rating writes are rare and short, so serialising all of
    them costs nothing here. Ordering by pk means two concurrent callers
    always take the locks in the same order and can't deadlock.

    Reading the players here is the point, not a side effect: a caller's
    match.player1 / match.player2 were typically loaded by the form, before
    any lock existed, so their in-memory rating may already be stale. The
    lock is worthless if the values used are the pre-lock ones.
    """
    return {
        player.pk: player
        for player in Player.objects.select_for_update().order_by("pk")
    }


def update_ratings_from_match(match):
    """
    Applies one match's rating change on top of both players' current
    ratings, and records a RatingHistory row for each.

    Only correct when this match is the newest one on record. A backdated
    match needs recompute_all_ratings() instead, since its result has to be
    applied to the ratings as they stood on its own date. Match.save()
    decides which of the two runs.
    """
    with transaction.atomic():
        players = _locked_players()
        player1 = players[match.player1_id]
        player2 = players[match.player2_id]

        score_a = score_from_match(match.score1, match.score2)
        new_r1, new_r2 = rating_update(player1.rating, player2.rating, score_a)

        player1.rating = new_r1
        player2.rating = new_r2
        player1.save(update_fields=["rating"])
        player2.save(update_fields=["rating"])

        RatingHistory.objects.bulk_create(
            [
                RatingHistory(player_id=player1.pk, match_id=match.pk, rating=new_r1),
                RatingHistory(player_id=player2.pk, match_id=match.pk, rating=new_r2),
            ]
        )


def recompute_all_ratings():
    """
    Rebuilds every rating from scratch: resets each player to their initial
    rating, clears rating history, and replays every match in chronological
    (date, id) order.

    Runs whenever the stored ratings can no longer be trusted: a backdated
    match, any match edit or deletion, a changed initial_rating, or the
    `recompute_ratings` command after a bulk import that bypassed save().

    The replay happens in memory. Ratings live in a dict and only the final
    value per player is written, which is what keeps this cheap: a fixed
    handful of queries instead of roughly six per match. It also removes the
    reason the match query couldn't be optimised before -- the loop used to
    read each player's freshly written rating back out of the database, so
    any upfront JOIN handed later iterations a stale snapshot and silently
    broke the replay. Nothing is read back now, and players are never
    reached through match.player1 / match.player2 at all, only by id.

    This is deliberately a full replay rather than a partial one starting at
    the affected date. Ratings here are derived from immutable inputs only
    (each player's initial_rating plus the match records), which makes this
    self-healing: whatever went wrong, running it again produces the correct
    answer. Replaying from a cutoff would mean reading the pre-cutoff
    ratings back out of RatingHistory, which promotes derived data into
    load-bearing state and turns any history bug into a permanent rating bug
    with no way to recover.

    Returns the number of matches replayed.
    """
    with transaction.atomic():
        players = _locked_players()
        ratings = {pk: player.initial_rating for pk, player in players.items()}

        RatingHistory.objects.all().delete()

        history = []
        count = 0

        for match in Match.objects.order_by("date", "id").iterator():
            p1_id = match.player1_id
            p2_id = match.player2_id

            score_a = score_from_match(match.score1, match.score2)
            new_r1, new_r2 = rating_update(ratings[p1_id], ratings[p2_id], score_a)

            ratings[p1_id] = new_r1
            ratings[p2_id] = new_r2

            history.append(
                RatingHistory(player_id=p1_id, match_id=match.pk, rating=new_r1)
            )
            history.append(
                RatingHistory(player_id=p2_id, match_id=match.pk, rating=new_r2)
            )
            count += 1

        for pk, player in players.items():
            player.rating = ratings[pk]

        # batch_size keeps a large rebuild from being sent as one enormous
        # statement. The history rows are created in replay order, so their
        # auto_now_add timestamps stay in that order too.
        Player.objects.bulk_update(players.values(), ["rating"], batch_size=1000)
        RatingHistory.objects.bulk_create(history, batch_size=1000)

    return count
