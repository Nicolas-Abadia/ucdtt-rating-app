"""Live leaderboard projections. No persisted counters or schema changes."""
from django.db.models import Count, F, IntegerField, OuterRef, Subquery, Window
from django.db.models.functions import Coalesce, Rank

from .models import Match, Player


def _result_count(role, won):
    own_score, other_score = ("score1", "score2") if role == "player1" else ("score2", "score1")
    comparison = "gt" if won else "lt"
    counts = (
        Match.objects.filter(**{
            role: OuterRef("pk"),
            f"{own_score}__{comparison}": F(other_score),
        })
        .order_by()
        .values(role)
        .annotate(total=Count("pk"))
        .values("total")
    )
    return Coalesce(Subquery(counts, output_field=IntegerField()), 0)


def leaderboard_queryset():
    """One SQL statement; independent subqueries avoid multiplying p1/p2 joins.

    Rank uses exact stored ratings (same ordering as the HTML leaderboard).
    Equal ratings share competition ranks: 1, 1, 3. Name/id only break display
    order ties, never rank ties. Rounding stays in Player.display_rating.
    """
    return (
        Player.objects.only("id", "name", "rating")
        .annotate(
            wins=_result_count("player1", True) + _result_count("player2", True),
            losses=_result_count("player1", False) + _result_count("player2", False),
            rank=Window(expression=Rank(), order_by=F("rating").desc()),
        )
        .order_by("-rating", "name", "pk")
    )
