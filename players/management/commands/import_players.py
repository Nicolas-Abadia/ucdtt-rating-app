import csv

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models.functions import Lower

from players.models import Player


class Command(BaseCommand):
    help = "Bulk import players from a CSV with a 'name' column and an optional 'rating' column"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to the CSV file to import")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be imported without writing anything",
        )

    def handle(self, *args, **options):
        rows = self.read_rows(options["csv_path"])

        # Printed because this command is normally pointed at the production
        # database by setting DATABASE_URL inline, so it should always be
        # obvious which database is about to be written to.
        db = connection.settings_dict
        host = db["HOST"] or "local socket"
        self.stdout.write(f"Target database: {host}/{db['NAME']}")

        to_create, skipped = self.build_players(rows)

        for line, reason in skipped:
            self.stdout.write(self.style.WARNING(f"  line {line}: {reason}"))

        if options["dry_run"]:
            self.stdout.write(
                f"Dry run: would create {len(to_create)} player(s) and "
                f"skip {len(skipped)} row(s). Nothing was written."
            )
            return

        with transaction.atomic():
            Player.objects.bulk_create(to_create, batch_size=500)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(to_create)} player(s), skipped {len(skipped)} row(s)."
            )
        )

    def read_rows(self, path):
        # utf-8-sig strips the byte-order mark that Excel and Google Sheets
        # prepend when exporting CSV. Without it the first column header parses
        # as "\ufeffname" and the file looks fine in an editor but fails here.
        try:
            with open(path, newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                if reader.fieldnames is None:
                    raise CommandError(f"{path} is empty.")
                if "name" not in reader.fieldnames:
                    found = ", ".join(reader.fieldnames)
                    raise CommandError(
                        f"The CSV needs a 'name' column. Found: {found}"
                    )
                # reader.line_num is the physical line in the file, which stays
                # correct even though DictReader silently drops blank lines.
                rows = [(reader.line_num, row) for row in reader]
        except FileNotFoundError:
            raise CommandError(f"No such file: {path}")
        except UnicodeDecodeError:
            raise CommandError(f"{path} is not valid UTF-8 text.")

        if not rows:
            raise CommandError("The CSV has a header row but no data rows.")
        return rows

    def build_players(self, rows):
        """
        Validates every row in Python before anything is written.

        bulk_create bypasses save(), and therefore full_clean(), so the
        MinValueValidator on rating never runs. The case-insensitive
        unique_player_name_ci constraint is enforced by the database, but a
        violation would abort the entire transaction and import nothing, so
        duplicates are filtered out here rather than left to fail the import.
        """
        existing = set(
            Player.objects.annotate(lowered=Lower("name")).values_list(
                "lowered", flat=True
            )
        )
        to_create = []
        skipped = []
        seen = set()

        for line, row in rows:
            name = (row.get("name") or "").strip()
            if not name:
                skipped.append((line, "blank name"))
                continue
            if len(name) > 200:
                skipped.append(
                    (line, f"name longer than 200 characters: {name[:40]}...")
                )
                continue

            # .lower() rather than .casefold() to stay consistent with the
            # database's Lower() in unique_player_name_ci.
            key = name.lower()
            if key in existing:
                skipped.append((line, f"already in the database: {name}"))
                continue
            if key in seen:
                skipped.append((line, f"duplicated within the file: {name}"))
                continue

            raw_rating = (row.get("rating") or "").strip()
            try:
                rating = int(raw_rating) if raw_rating else 1200
            except ValueError:
                skipped.append(
                    (line, f"rating is not a whole number: {raw_rating!r}")
                )
                continue
            if rating < 100:
                skipped.append((line, f"rating below the minimum of 100: {rating}"))
                continue

            seen.add(key)
            # initial_rating matters as much as rating. recompute_all_ratings()
            # resets every player to initial_rating before replaying the match
            # history, so a seeded rating stored only in `rating` is silently
            # wiped the first time any match is edited, deleted or backdated.
            to_create.append(
                Player(name=name, rating=rating, initial_rating=rating)
            )

        return to_create, skipped
