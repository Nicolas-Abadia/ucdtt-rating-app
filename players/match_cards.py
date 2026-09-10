"""Read-only annotations for the optional match-card API representation.

History is ordered by match (date, pk), never by the history write timestamp:
replays recreate those rows. No rating replay or writes occur on a GET.
"""
from django.db.models import FloatField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce

from .models import Match, RatingHistory


def with_match_card_ratings(queryset):
    annotations = {}
    earlier_match = (
        Q(match__date__lt=OuterRef("date"))
        | Q(match__date=OuterRef("date"), match_id__lt=OuterRef("pk"))
    )
    for slot in (1, 2):
        history = RatingHistory.objects.filter(player_id=OuterRef(f"player{slot}_id"))
        previous = history.filter(earlier_match).order_by("-match__date", "-match_id", "-pk")
        current = history.filter(match_id=OuterRef("pk")).order_by("-pk")
        previous_match = Match.objects.filter(
            Q(player1_id=OuterRef(f"player{slot}_id"))
            | Q(player2_id=OuterRef(f"player{slot}_id"))
        ).filter(
            Q(date__lt=OuterRef("date"))
            | Q(date=OuterRef("date"), pk__lt=OuterRef("pk"))
        ).order_by("-date", "-pk")
        # A missing history row must not silently substitute an older match
        # or an initial rating. The serializer checks these two IDs agree.
        annotations[f"card_previous{slot}_match"] = Subquery(previous_match.values("pk")[:1])
        annotations[f"card_previous{slot}_history_match"] = Subquery(previous.values("match_id")[:1])
        annotations[f"card_rating{slot}_before"] = Coalesce(
            Subquery(previous.values("rating")[:1], output_field=FloatField()),
            f"player{slot}__initial_rating",
            output_field=FloatField(),
        )
        annotations[f"card_rating{slot}_after"] = Subquery(
            current.values("rating")[:1], output_field=FloatField()
        )
    return queryset.select_related("player1", "player2").annotate(**annotations)
