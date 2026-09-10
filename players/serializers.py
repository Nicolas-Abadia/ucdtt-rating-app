from django.utils import timezone
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


class MatchCardSerializer(MatchListSerializer):
    """Opt-in card fields, without repeating the full rating_changes payload."""

    player1_name = serializers.CharField(source="player1.name", read_only=True)
    player2_name = serializers.CharField(source="player2.name", read_only=True)
    player1_rating = serializers.SerializerMethodField()
    player2_rating = serializers.SerializerMethodField()

    class Meta(MatchListSerializer.Meta):
        fields = MatchListSerializer.Meta.fields + [
            "player1_name", "player2_name", "player1_rating", "player2_rating",
        ]

    @staticmethod
    def rating_summary(obj, slot):
        if getattr(obj, f"card_previous{slot}_match", None) != getattr(obj, f"card_previous{slot}_history_match", None):
            return None
        before = getattr(obj, f"card_rating{slot}_before", None)
        after = getattr(obj, f"card_rating{slot}_after", None)
        if before is None or after is None:
            return None
        # Match Player.display_rating's whole-number presentation. The delta
        # reconciles the displayed endpoints; stored ratings remain exact.
        before, after = round(before), round(after)
        change = after - before
        return {
            "rating_before": before,
            "rating_after": after,
            "change": change,
            "direction": "up" if change > 0 else "down" if change < 0 else "unchanged",
        }

    def get_player1_rating(self, obj):
        return self.rating_summary(obj, 1)

    def get_player2_rating(self, obj):
        return self.rating_summary(obj, 2)


class MatchDetailCardSerializer(MatchCardSerializer):
    """Opt-in rich detail, retaining the original detail's rating_changes."""

    rating_changes = RatingHistorySerializer(many=True, read_only=True)

    class Meta(MatchCardSerializer.Meta):
        fields = MatchCardSerializer.Meta.fields + ["rating_changes"]


class PlayerWriteSerializer(serializers.ModelSerializer):
    """Officer create/edit. rating stays derived: it is seeded from
    initial_rating on create and never written directly, matching
    PlayerForm in the HTML app."""

    class Meta:
        model = Player
        fields = ["name", "initial_rating", "style", "grip"]

    def validate_name(self, value):
        # The case-insensitive unique constraint is functional (Lower), so
        # DRF does not surface it as a field error on its own.
        queryset = Player.objects.filter(name__iexact=value)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("A player with this name already exists.")
        return value

    def create(self, validated_data):
        # Set before saving so this is one INSERT, like AddPlayerView.
        validated_data["rating"] = validated_data["initial_rating"]
        return super().create(validated_data)

    def update(self, instance, validated_data):
        initial_changed = (
            "initial_rating" in validated_data
            and validated_data["initial_rating"] != instance.initial_rating
        )
        player = super().update(instance, validated_data)
        if initial_changed:
            # Like EditPlayerView: changing the seed invalidates every
            # derived rating, so replay immediately.
            from ratings.services import recompute_all_ratings
            recompute_all_ratings()
        return player


class MatchWriteSerializer(serializers.ModelSerializer):
    """Officer log/correct a match. Rating side effects live in
    Match.save()/delete(); this serializer mirrors the form rules so the
    API rejects exactly what the HTML app rejects."""

    class Meta:
        model = Match
        fields = ["player1", "player2", "score1", "score2", "date"]

    def validate(self, attrs):
        player1 = attrs.get("player1", self.instance.player1 if self.instance else None)
        player2 = attrs.get("player2", self.instance.player2 if self.instance else None)
        score1 = attrs.get("score1", self.instance.score1 if self.instance else None)
        score2 = attrs.get("score2", self.instance.score2 if self.instance else None)
        date = attrs.get("date", self.instance.date if self.instance else None)
        errors = {}
        if player1 is not None and player1 == player2:
            errors["player2"] = "A player cannot play a match against themselves."
        if score1 is not None and score1 == score2:
            errors["score2"] = "One player must win."
        if date is not None and date > timezone.now():
            errors["date"] = "Match date cannot be in the future."
        if errors:
            raise serializers.ValidationError(errors)
        if None not in (player1, player2, score1, score2) and date is not None:
            # The duplicate guard is a row-level unique constraint, which a
            # save would report as a 500. Checked here as a 400 instead.
            duplicate = Match.objects.filter(
                player1=player1, player2=player2,
                score1=score1, score2=score2, date=date,
            )
            if self.instance is not None:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise serializers.ValidationError(
                    {"non_field_errors": ["This identical match has already been logged."]})
        return attrs


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
