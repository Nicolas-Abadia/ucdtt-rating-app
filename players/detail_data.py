"""Read-only projections for React detail pages. Never replay ratings on GET."""
from datetime import timedelta

from django.db.models import Count, F, Max, Q
from django.utils import timezone

from .models import Match, Player


def player_matches(player_id):
    return Match.objects.filter(Q(player1_id=player_id) | Q(player2_id=player_id))


def wins_for(player_id):
    return (Q(player1_id=player_id, score1__gt=F("score2"))
            | Q(player2_id=player_id, score2__gt=F("score1")))


def profile_payload(player):
    end = timezone.now()
    start = end - timedelta(days=90)
    matches = player_matches(player.pk)
    counts = matches.aggregate(
        total=Count("pk"), wins=Count("pk", filter=wins_for(player.pk)),
        recent=Count("pk", filter=Q(date__gte=start, date__lte=end)),
    )
    history = player.rating_history.filter(match__isnull=False)
    peak = history.aggregate(peak=Max("rating"))["peak"]
    points = list(history.filter(match__date__gte=start, match__date__lte=end)
                  .order_by("match__date", "match_id", "pk")
                  .values("match_id", "match__date", "rating"))
    return {
        "id": player.pk, "name": player.name,
        "style": player.style, "grip": player.grip,
        # Registration date, matching the server-rendered player detail page.
        "created_date": player.created_date.isoformat(),
        "display_rating": player.display_rating,
        "initial_rating": player.initial_rating,
        # Competition rank matches the leaderboard, including equal-rating ties.
        # Filtering the leaderboard's window before ranking would always give 1.
        "rank": 1 + Player.objects.filter(rating__gt=player.rating).count(),
        "wins": counts["wins"], "losses": counts["total"] - counts["wins"],
        "total_matches": counts["total"],
        "highest_rating": round(max(player.initial_rating, player.rating,
                                    peak if peak is not None else player.initial_rating)),
        "win_percentage": round(100 * counts["wins"] / counts["total"], 1) if counts["total"] else None,
        "history_start": start, "history_end": end,
        "history_complete": len({point["match_id"] for point in points}) == counts["recent"],
        "rating_history": [{"match": point["match_id"], "date": point["match__date"],
                            "rating": round(point["rating"])} for point in points],
    }


def pair_meetings(match):
    """Every meeting between the pair, newest first.

    Deliberately not relative to the selected match: the head-to-head shown
    on a match detail page is the pair's global record, so earlier, current,
    and later meetings all count.
    """
    pair = (Q(player1_id=match.player1_id, player2_id=match.player2_id)
            | Q(player1_id=match.player2_id, player2_id=match.player1_id))
    return Match.objects.filter(pair).order_by("-date", "-pk")
