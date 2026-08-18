from django.core.management.base import BaseCommand
from players.models import Player
from ratings.services import recompute_all_ratings


class Command(BaseCommand):
    help = "Recompute all player ratings from match history"

    def handle(self, *args, **options):
        self.stdout.write("Recomputing ratings from matches...")
        count = recompute_all_ratings()
        self.stdout.write(
            self.style.SUCCESS(
                f"Recomputed ratings for {count} match(es). "
                f"Updated {Player.objects.count()} player(s)."
            )
        )
