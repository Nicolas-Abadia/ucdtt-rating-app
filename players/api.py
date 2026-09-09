from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import mixins, viewsets
from rest_framework.routers import DefaultRouter

from .models import Match, Player
from .leaderboard import leaderboard_queryset
from .serializers import (
    MatchSerializer,
    MatchListSerializer,
    LeaderboardSerializer,
    PlayerListSerializer,
    PlayerDetailSerializer,
)


class PlayerViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Player.objects.order_by("-rating")

    def get_serializer_class(self):
        # Dynamically switch serializers based on the requested API action
        if self.action == 'retrieve':
            return PlayerDetailSerializer
        return PlayerListSerializer

    # Used instead of DRF's SearchFilter because search matches for names or IDs,
    # which the built-in filter can't express.
    def get_queryset(self):
        queryset = super().get_queryset()

        query = self.request.query_params.get("q", "").strip()

        if not query:
            return queryset

        condition = Q(name__icontains=query)

        if query.isdigit():
            condition |= Q(pk=int(query))

        return queryset.filter(condition)


class MatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        Match.objects.select_related("player1", "player2").order_by("-date", "-pk")
    )

    def get_serializer_class(self):
        return MatchSerializer if self.action == "retrieve" else MatchListSerializer

    def get_queryset(self):

        queryset = super().get_queryset()

        query = self.request.query_params.get("q", "").strip()

        if query:
            condition = (
                Q(player1__name__icontains=query)
                | Q(player2__name__icontains=query)
            )
            if query.isdigit():
                player_id = int(query)
                condition |= Q(player1_id=player_id) | Q(player2_id=player_id)
            queryset = queryset.filter(condition)

        if self.action == "retrieve":
            queryset = queryset.prefetch_related("rating_changes__match")

        try:
            day = parse_date(self.request.query_params.get("date", "").strip())
        except ValueError:
            day = None

        if day is not None:
            queryset = queryset.filter(date__date=day)

        return queryset


class LeaderboardViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Complete compact standings for a club-sized roster.

    Deliberately unpaginated. General player/match lists remain paginated.
    React filters this full roster locally without changing server ranks.
    """

    serializer_class = LeaderboardSerializer
    pagination_class = None

    def get_queryset(self):
        return leaderboard_queryset()


router = DefaultRouter()
router.register("players", PlayerViewSet)
router.register("matches", MatchViewSet)
router.register("leaderboard", LeaderboardViewSet, basename="leaderboard")
