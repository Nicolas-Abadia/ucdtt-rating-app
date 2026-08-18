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
    score1 = models.IntegerField()
    score2 = models.IntegerField()
    date = models.DateTimeField("date")

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
