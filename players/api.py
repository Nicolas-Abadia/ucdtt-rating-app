from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import viewsets
from rest_framework.routers import DefaultRouter

from .models import Match, Player
from .serializers import (
    MatchSerializer,
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
        Match.objects.select_related("player1", "player2").order_by("-date")
    )

    serializer_class = MatchSerializer

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

        day = parse_date(self.request.query_params.get("date", "").strip())

        if day is not None:
            queryset = queryset.filter(date__date=day)

        return queryset


router = DefaultRouter()
router.register("players", PlayerViewSet)
router.register("matches", MatchViewSet)
