from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone

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
            models.UniqueConstraint(
                fields=['player1', 'player2', 'score1', 'score2', 'date'],
                name='prevent_identical_match_duplicates',
                violation_error_message="This identical match has already been logged."
            ),
            models.CheckConstraint(
                condition=models.Q(score1__gte=0) & models.Q(score2__gte=0),
                name="match_scores_non_negative",
            ),
            models.CheckConstraint(
                condition=~models.Q(player1=models.F("player2")),
                name="match_players_distinct",
                violation_error_message="A player cannot play a match against themselves.",
            ),
        ]

    def clean(self):
        super().clean()

        if self.score1 is not None and self.score1 < 0:
            raise ValidationError({"score1": "Score cannot be negative."})

        if self.score2 is not None and self.score2 < 0:
            raise ValidationError({"score2": "Score cannot be negative."})

        if self.score1 is not None and self.score2 is not None and self.score1 == self.score2:
            raise ValidationError("One player must win.")

        if self.date is not None and self.date > timezone.now():
            raise ValidationError({"date": "Match date cannot be in the future."}) 

    def save(self, *args, **kwargs):
        """
        Keeps player ratings in sync with the match record.

        On creation, updates both players' ratings via
        ratings.services.update_ratings_from_match. This runs for any
        Match creation (LogMatchView, the admin, the shell, a future API,
        etc).

        If the new match is dated earlier than an already-existing match
        (a backdated/out-of-order match), a single incremental update
        would apply today's ratings instead of the ratings that existed
        as of that date. In that case a full recompute runs instead,
        replaying every match in chronological order via
        ratings.services.recompute_all_ratings.

        On edit, a full recompute always runs. Every field on this model
        (both players, both scores, the date) feeds the rating
        calculation, so there is no such thing as a rating-irrelevant
        edit here: changing any of them invalidates this match's result
        and every result computed after it.

        The match write and the rating write share one transaction, so a
        failure partway through can't leave a stored match whose rating
        change was never applied.

        Bulk operations (bulk_create/queryset.update) bypass
        save() and are intentionally not covered here. Follow a bulk
        match import with the `recompute_ratings` management command
        instead of relying on per-row updates.
        """
        from ratings.services import (
            recompute_all_ratings,
            update_ratings_from_match,
        )

        is_new = self._state.adding
        with transaction.atomic():
            self.full_clean()
            super().save(*args, **kwargs)
            if not is_new:
                recompute_all_ratings()
                return
            is_out_of_order = (
                Match.objects.filter(date__gt=self.date).exclude(pk=self.pk).exists()
            )
            if is_out_of_order:
                recompute_all_ratings()
            else:
                update_ratings_from_match(self)

    def delete(self, *args, **kwargs):
        """
        Removing a match invalidates every rating computed from it
        onward, so ratings are replayed from scratch afterwards. The
        delete and the recompute share one transaction.

        As with save(), a bulk queryset.delete() bypasses this. MatchAdmin
        handles the admin's bulk delete action explicitly; any other bulk
        delete needs the `recompute_ratings` command afterwards.
        """
        from ratings.services import recompute_all_ratings

        with transaction.atomic():
            result = super().delete(*args, **kwargs)
            recompute_all_ratings()
        return result

    def __str__(self):
        return f"{self.player1} vs {self.player2} ({self.score1}-{self.score2}) on {self.date}"

class RatingHistory(models.Model):
    player = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="rating_history")
    # CASCADE, not PROTECT: history rows are derived data that
    # recompute_all_ratings() rebuilds from the matches. PROTECT here made a
    # match undeletable as soon as it had history, which is every match.
    # Deleting a match now drops its history rows, and the recompute that
    # follows regenerates the full history.
    match = models.ForeignKey(Match, on_delete=models.CASCADE, null=True, blank=True, related_name="rating_changes")
    rating = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.player.name}: {self.rating}"
