from django.core.validators import MinValueValidator
from django.db import models

# Create your models here.


class Player(models.Model):
    name = models.CharField(max_length=200)
    rating = models.IntegerField(default=1200, validators=[MinValueValidator(100)])
    initial_rating = models.IntegerField(default=1200, validators=[MinValueValidator(100)])
    created_date = models.DateTimeField("created date", auto_now_add=True)

    def __str__(self):
        return self.name

class Match(models.Model):
    player1 = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="matches_as_p1")
    player2 = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="matches_as_p2")
    score1 = models.IntegerField(validators=[MinValueValidator(0)])
    score2 = models.IntegerField(validators=[MinValueValidator(0)])
    date = models.DateTimeField("date", db_index=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(score1__gte=0) & models.Q(score2__gte=0),
                name="match_scores_non_negative",
            ),
            models.CheckConstraint(
                condition=~models.Q(player1=models.F("player2")),
                name="match_players_distinct",
            ),
        ]

    def save(self, *args, **kwargs):
        """
        On creation, updates both players' ratings via
        ratings.services.update_ratings_from_match. This runs for any
        Match creation (LogMatchView, the admin, the shell, a future API,
        etc), not just one call site.

        If the new match is dated earlier than an already-existing match
        (a backdated/out-of-order match), a single incremental update
        would apply today's ratings instead of the ratings that existed
        as of that date. In that case a full recompute runs instead,
        replaying every match in chronological order via
        ratings.services.recompute_all_ratings.

        Bulk operations (bulk_create/queryset.update) bypass
        save() and are intentionally not covered here. Follow a bulk
        match import with the `recompute_ratings` management command
        instead of relying on per-row updates.
        """
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            from ratings.services import (
                recompute_all_ratings,
                update_ratings_from_match,
            )
            is_out_of_order = (
                Match.objects.filter(date__gt=self.date).exclude(pk=self.pk).exists()
            )
            if is_out_of_order:
                recompute_all_ratings()
            else:
                update_ratings_from_match(self)

    def __str__(self):
        return f"{self.player1} vs {self.player2} ({self.score1}-{self.score2}) on {self.date}"

class RatingHistory(models.Model):
    player = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="rating_history")
    match = models.ForeignKey(Match, on_delete=models.PROTECT, null=True, blank=True, related_name="rating_changes")
    rating = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.player.name}: {self.rating}"
