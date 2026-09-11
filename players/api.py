from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db.models import ProtectedError, Q
from django.db.models.functions import TruncDate
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.routers import DefaultRouter

from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Match, Player
from .detail_data import pair_meetings, player_matches, profile_payload
from .leaderboard import leaderboard_queryset
from .match_cards import with_match_card_ratings
from .serializers import (
    MatchSerializer,
    MatchListSerializer,
    MatchCardSerializer,
    MatchDetailCardSerializer,
    LeaderboardSerializer,
    PlayerListSerializer,
    PlayerDetailSerializer,
    PlayerWriteSerializer,
    MatchWriteSerializer,
)


class PlayerViewSet(viewsets.ModelViewSet):

    # Reads stay public; create/update/delete require an officer's JWT.
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = Player.objects.order_by("-rating")

    def get_serializer_class(self):
        # Dynamically switch serializers based on the requested API action
        if self.action in ("create", "update", "partial_update"):
            return PlayerWriteSerializer
        if self.action == 'retrieve':
            return PlayerDetailSerializer
        return PlayerListSerializer

    def destroy(self, request, *args, **kwargs):
        # Player is PROTECTed by Match and RatingHistory, so deleting someone
        # who has played is refused rather than erroring, like DeletePlayerView.
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "This player has recorded matches and cannot be deleted. "
                            "Those matches are what the other players' ratings were computed from."},
                status=status.HTTP_409_CONFLICT,
            )

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

    @action(detail=True, methods=["get"])
    def profile(self, request, pk=None):
        # Read-only projection: totals, rank, and rating history. Never
        # replays or recomputes ratings.
        return Response(profile_payload(self.get_object()))

    @action(detail=True, methods=["get"])
    def matches(self, request, pk=None):
        player = self.get_object()
        queryset = with_match_card_ratings(
            player_matches(player.pk).select_related("player1", "player2")
        ).order_by("-date", "-pk")
        page = self.paginate_queryset(queryset)
        serializer = MatchCardSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)


class MatchViewSet(viewsets.ModelViewSet):
    # Reads stay public; log/edit/delete require an officer's JWT. Rating
    # side effects of every write live in Match.save()/delete().
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = (
        Match.objects.select_related("player1", "player2").order_by("-date", "-pk")
    )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MatchWriteSerializer
        if self.action == "retrieve":
            if self.request.query_params.get("include") == "card":
                return MatchDetailCardSerializer
            return MatchSerializer
        if self.request.query_params.get("include") == "card":
            return MatchCardSerializer
        return MatchListSerializer

    def get_queryset(self):

        queryset = super().get_queryset()

        query = self.request.query_params.get("q", "").strip()

        if query:
            condition = (
                Q(player1__name__icontains=query)
                | Q(player2__name__icontains=query)
            )
            digits = query.lstrip("0") or "0"
            if digits.isascii() and digits.isdecimal() and len(digits) <= 19:
                player_id = int(digits)
                if 0 < player_id <= 9223372036854775807:
                    condition |= Q(player1_id=player_id) | Q(player2_id=player_id)
            queryset = queryset.filter(condition)

        match_id = self.request.query_params.get("match_id", "").strip()
        if match_id:
            # Guard before int(): malformed and out-of-range IDs match nothing.
            digits = match_id.lstrip("0") or "0"
            if not digits.isascii() or not digits.isdecimal() or len(digits) > 19:
                queryset = queryset.none()
            elif not 0 < int(digits) <= 9223372036854775807:
                queryset = queryset.none()
            else:
                queryset = queryset.filter(pk=int(digits))

        if self.action == "retrieve":
            queryset = queryset.prefetch_related("rating_changes__match")
        if self.request.query_params.get("include") == "card":
            queryset = with_match_card_ratings(queryset)

        try:
            day = parse_date(self.request.query_params.get("date", "").strip())
        except ValueError:
            day = None

        if day is not None:
            zone_name = self.request.query_params.get("tz", "").strip()
            if zone_name:
                try:
                    zone = ZoneInfo(zone_name)
                except (ZoneInfoNotFoundError, ValueError):
                    raise ValidationError({"tz": "Use a valid IANA timezone."})
                # Match the calendar day displayed by the browser, including
                # daylight-saving boundaries, without relying on a cross-site cookie.
                queryset = queryset.alias(card_local_day=TruncDate("date", tzinfo=zone)).filter(card_local_day=day)
            else:
                # Preserve the existing API behavior for callers without tz.
                queryset = queryset.filter(date__date=day)

        return queryset

    @action(detail=True, methods=["get"], url_path="head-to-head")
    def head_to_head(self, request, pk=None):
        match = self.get_object()
        # The record is the pair's global tally: the selected match and any
        # later meetings count too, not just the meetings that came before it.
        meetings = pair_meetings(match)
        record = {"player1_wins": 0, "player2_wins": 0}
        for meeting in meetings:
            winner_id = meeting.player1_id if meeting.score1 > meeting.score2 else meeting.player2_id
            if winner_id == match.player1_id:
                record["player1_wins"] += 1
            elif winner_id == match.player2_id:
                record["player2_wins"] += 1
        queryset = with_match_card_ratings(meetings.select_related("player1", "player2"))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = MatchCardSerializer(page, many=True, context={"request": request})
            response = self.get_paginated_response(serializer.data)
            response.data["record"] = record
            return response
        serializer = MatchCardSerializer(queryset, many=True, context={"request": request})
        return Response({"count": queryset.count(), "next": None, "previous": None,
                          "results": serializer.data, "record": record})


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
