from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from players import imports


class Command(BaseCommand):
    help = (
        "Bulk import matches from a CSV with player1, player2, score1, "
        "score2 and date columns. Both players must already be on the "
        "roster. A date with no UTC offset is read in settings.TIME_ZONE."
    )

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
        # obvious which database is about to be written to. The timezone is
        # printed for the same reason: a naive date in the file is read in
        # it, and a command run has no browser to take it from.
        db = connection.settings_dict
        host = db["HOST"] or "local socket"
        self.stdout.write(f"Target database: {host}/{db['NAME']}")
        self.stdout.write(f"Dates without an offset are read as {settings.TIME_ZONE}")

        to_create, skipped = self.build_matches(rows)

        for line, reason in skipped:
            self.stdout.write(self.style.WARNING(f"  line {line}: {reason}"))

        if options["dry_run"]:
            self.stdout.write(
                f"Dry run: would create {len(to_create)} match(es) and "
                f"skip {len(skipped)} row(s). Nothing was written."
            )
            return

        created, replayed = imports.save_matches(to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created} match(es), skipped {len(skipped)} row(s). "
                f"Replayed {replayed} match(es) to rebuild ratings."
            )
        )

    def read_rows(self, path):
        """
        Reading and validation live in players/imports.py so that this
        command and the officer-facing upload view cannot drift apart and
        accept different files.

        CsvImportError becomes CommandError here, which is what prints a
        single clean line instead of a traceback.
        """
        try:
            return imports.read_file(path, imports.MATCH_COLUMNS)
        except imports.CsvImportError as error:
            raise CommandError(str(error))

    def build_matches(self, rows):
        return imports.build_matches(rows)
