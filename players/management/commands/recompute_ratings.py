from django.core.management.base import BaseCommand
from django.db import transaction
from players.models import Player, Match, RatingHistory
from ratings.services import update_ratings_from_match


class Command(BaseCommand):
    help = "Recompute all player ratings from match history"

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write("Resetting player ratings to initial ratings...")
            for player in Player.objects.all():
                player.rating = player.initial_rating
                player.save()

            self.stdout.write("Clearing rating history...")
            RatingHistory.objects.all().delete()

            self.stdout.write("Recomputing ratings from matches...")
            matches = Match.objects.order_by("date", "id")
            count = 0
            for match in matches:
                update_ratings_from_match(match)
                count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Recomputed ratings for {count} match(es). "
                f"Updated {Player.objects.count()} player(s)."
            )
        )
