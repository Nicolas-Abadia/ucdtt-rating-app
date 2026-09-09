from rest_framework import serializers
from django.db.models import Q
from players.models import Player, Match, RatingHistory


class RatingHistorySerializer(serializers.ModelSerializer):

    date = serializers.DateTimeField(source="match.date", read_only=True)

    class Meta:
        model = RatingHistory
        fields = [
            "player",
            "match",
            "rating",
            "date",
            "timestamp"
        ]


class MatchSerializer(serializers.ModelSerializer):

    # Self-link for browsable-API navigation. Relations stay as plain ids:
    # the React client builds routes from ids, and future write endpoints
    # will accept ids, not URLs.
    url = serializers.HyperlinkedIdentityField(
        view_name="match-detail", read_only=True
    )
    rating_changes = RatingHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Match
        fields = [
            "id",
            "url",
            "player1",
            "player2",
            "score1",
            "score2",
            "date",
            "rating_changes",
        ]


class MatchListSerializer(serializers.ModelSerializer):
    """Compact match summary; rating history belongs to match detail."""

    url = serializers.HyperlinkedIdentityField(view_name="match-detail", read_only=True)

    class Meta:
        model = Match
        fields = ["id", "url", "player1", "player2", "score1", "score2", "date"]


class LeaderboardSerializer(serializers.ModelSerializer):
    rank = serializers.IntegerField(read_only=True)
    wins = serializers.IntegerField(read_only=True)
    losses = serializers.IntegerField(read_only=True)
    display_rating = serializers.IntegerField(read_only=True)

    class Meta:
        model = Player
        fields = ["id", "name", "rank", "display_rating", "wins", "losses"]
        read_only_fields = fields


class PlayerListSerializer(serializers.ModelSerializer):

    url = serializers.HyperlinkedIdentityField(
        view_name="player-detail", read_only=True
    )

    class Meta:
        model = Player
        fields = [
            "id",
            "url",
            "name",
            "display_rating",
            "rating",
            "initial_rating",
            "style",
            "grip",
            "created_date",
        ]


class PlayerDetailSerializer(serializers.ModelSerializer):

    url = serializers.HyperlinkedIdentityField(
        view_name="player-detail", read_only=True
    )
    rating_history = RatingHistorySerializer(many=True, read_only=True)
    matches = serializers.SerializerMethodField()

    class Meta:
        model = Player
        fields = [
            "id",
            "url",
            "name",
            "display_rating",
            "rating",
            "initial_rating",
            "style",
            "grip",
            "created_date",
            "matches",
            "rating_history",
        ]

    def get_matches(self, obj):
        queryset = Match.objects.filter(Q(player1=obj) | Q(player2=obj)).order_by("-date")
        serializer = MatchListSerializer(queryset, many=True, context=self.context)
        return serializer.data
