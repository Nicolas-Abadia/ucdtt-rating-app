"""
CSV import logic shared by the management commands and the officer-facing
upload views.

Both entry points parse and validate identically, so a file that imports
cleanly from the command line behaves the same way through the browser. The
only difference is where the file comes from and how the result is reported.

Writes go through bulk_create, which bypasses Model.save() and therefore
full_clean(), so every row is checked here before anything is written. For
matches that is also the point: Match.save() recomputes ratings per match,
so importing N matches through it would replay the entire history N times.
A bulk insert followed by one recompute_all_ratings() produces the same
ratings in a single pass, and stays correct when the file is not in
chronological order.
"""

import csv
from datetime import datetime, time

from django.db import transaction
from django.db.models.functions import Lower
from django.utils import dateparse, timezone

from players.models import Match, Player

# A roster or a season of matches is a few tens of kilobytes. This limit
# exists so that a mis-selected file (a video, a database dump) is rejected
# before it is read into memory, not to constrain real imports.
MAX_UPLOAD_BYTES = 2 * 1024 * 1024

PLAYER_COLUMNS = ["name"]
MATCH_COLUMNS = ["player1", "player2", "score1", "score2", "date"]

DEFAULT_RATING = 1200
MIN_RATING = 100
MAX_NAME_LENGTH = 200


class CsvImportError(Exception):
    """
    The file as a whole is unusable: unreadable, wrong columns, no rows.

    Distinct from a skipped row. A skipped row is reported and the rest of
    the file still imports; this aborts the import.
    """


def read_rows(stream, required_columns, label):
    """
    Parses a text stream into a list of (line_number, row_dict).

    stream must yield text rather than bytes, and must be opened with
    newline="" and encoding="utf-8-sig". The BOM matters: Excel and Google
    Sheets prepend one on export, and without utf-8-sig the first header
    parses as "\\ufeffname", which looks correct in an editor and fails here.

    label appears in the error messages: a path for the commands, the
    uploaded filename for the views.
    """
    try:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise CsvImportError(f"{label} is empty.")
        for column in required_columns:
            if column not in reader.fieldnames:
                found = ", ".join(reader.fieldnames)
                raise CsvImportError(
                    f"The CSV needs a '{column}' column. Found: {found}"
                )
        # reader.line_num is the physical line in the file, which stays
        # correct even though DictReader silently drops blank lines.
        rows = [(reader.line_num, row) for row in reader]
    except UnicodeDecodeError:
        raise CsvImportError(f"{label} is not valid UTF-8 text.")

    if not rows:
        raise CsvImportError("The CSV has a header row but no data rows.")
    return rows


def read_file(path, required_columns):
    """
    Opens a CSV on disk and returns its rows.

    Used by the management commands. The upload views wrap the request's
    file object in a TextIOWrapper and call read_rows directly, since an
    upload has no path.
    """
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            return read_rows(fh, required_columns, path)
    except FileNotFoundError:
        raise CsvImportError(f"No such file: {path}")


def build_players(rows):
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
        if len(name) > MAX_NAME_LENGTH:
            skipped.append(
                (
                    line,
                    f"name longer than {MAX_NAME_LENGTH} characters: "
                    f"{name[:40]}...",
                )
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
            rating = int(raw_rating) if raw_rating else DEFAULT_RATING
        except ValueError:
            skipped.append(
                (line, f"rating is not a whole number: {raw_rating!r}")
            )
            continue
        if rating < MIN_RATING:
            skipped.append(
                (line, f"rating below the minimum of {MIN_RATING}: {rating}")
            )
            continue

        seen.add(key)
        # initial_rating matters as much as rating. recompute_all_ratings()
        # resets every player to initial_rating before replaying the match
        # history, so a seeded rating stored only in `rating` is silently
        # wiped the first time any match is edited, deleted or backdated.
        player = Player(name=name, rating=rating, initial_rating=rating)
        # Read by the upload view to report the row without touching the
        # database. Ignored by bulk_create.
        player._label = f"{name} ({rating})"
        to_create.append(player)

    return to_create, skipped


def save_players(to_create):
    """
    Inserts the players. No recompute: adding a player cannot change
    anybody else's rating, and a seeded rating is already stored in both
    rating and initial_rating.
    """
    with transaction.atomic():
        Player.objects.bulk_create(to_create, batch_size=500)
    return len(to_create)


def parse_csv_datetime(raw):
    """
    Returns an aware datetime for a CSV date cell, or raises ValueError.

    A cell carrying no UTC offset is naive, and is read in the timezone that
    is active for the caller: the browser's timezone for an upload (set by
    players.middleware.TimezoneMiddleware) and settings.TIME_ZONE for a
    management command. That is deliberate. "19:30" in a file means the same
    19:30 the uploader sees everywhere else on the site.
    """
    value = dateparse.parse_datetime(raw)
    if value is None:
        day = dateparse.parse_date(raw)
        if day is None:
            raise ValueError(raw)
        # A date with no time is taken as midnight, matching the behaviour
        # of the match form's "%Y-%m-%d" input format.
        value = datetime.combine(day, time.min)
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    return value


def build_matches(rows):
    """
    Validates every row against the rules Match enforces, before anything is
    written.

    bulk_create skips full_clean(), so the future-date rule from
    Match.clean() is applied here. The database constraints (distinct
    players, no tie, no identical duplicate) would each be enforced, but one
    violation aborts the whole transaction and imports nothing, so offending
    rows are skipped instead.

    Player names are matched case-insensitively against players who already
    exist. A match import never creates players: a name that is not on the
    roster is far more likely to be a typo than a new member, and inventing
    one would seed a rating nobody chose.
    """
    players_by_name = {
        name.lower(): pk for pk, name in Player.objects.values_list("pk", "name")
    }
    existing = set(
        Match.objects.values_list(
            "player1_id", "player2_id", "score1", "score2", "date"
        )
    )
    now = timezone.now()
    to_create = []
    skipped = []
    seen = set()

    for line, row in rows:
        name1 = (row.get("player1") or "").strip()
        name2 = (row.get("player2") or "").strip()
        if not name1 or not name2:
            skipped.append((line, "blank player name"))
            continue

        pk1 = players_by_name.get(name1.lower())
        pk2 = players_by_name.get(name2.lower())
        unknown = [
            name for name, pk in ((name1, pk1), (name2, pk2)) if pk is None
        ]
        if unknown:
            skipped.append((line, f"not on the roster: {', '.join(unknown)}"))
            continue
        if pk1 == pk2:
            skipped.append(
                (line, f"a player cannot play themselves: {name1}")
            )
            continue

        scores = []
        bad_score = None
        for column in ("score1", "score2"):
            raw_score = (row.get(column) or "").strip()
            try:
                scores.append(int(raw_score))
            except ValueError:
                bad_score = (
                    f"{column} is not a whole number: {raw_score!r}"
                )
                break
        if bad_score:
            skipped.append((line, bad_score))
            continue

        score1, score2 = scores
        if score1 < 0 or score2 < 0:
            skipped.append((line, f"negative score: {score1}-{score2}"))
            continue
        if score1 == score2:
            skipped.append((line, f"one player must win: {score1}-{score2}"))
            continue

        raw_date = (row.get("date") or "").strip()
        if not raw_date:
            skipped.append((line, "blank date"))
            continue
        try:
            date = parse_csv_datetime(raw_date)
        except ValueError:
            skipped.append(
                (line, f"date is not a date and time: {raw_date!r}")
            )
            continue
        if date > now:
            skipped.append((line, f"date is in the future: {raw_date}"))
            continue

        key = (pk1, pk2, score1, score2, date)
        if key in existing:
            skipped.append((line, "already in the database"))
            continue
        if key in seen:
            skipped.append((line, "duplicated within the file"))
            continue

        seen.add(key)
        match = Match(
            player1_id=pk1,
            player2_id=pk2,
            score1=score1,
            score2=score2,
            date=date,
        )
        # Read by the upload view to report the row. Built from the names
        # already in hand, so reporting an import does not issue a query per
        # row the way str(match) would.
        match._label = f"{name1} vs {name2} {score1}-{score2} on {raw_date}"
        to_create.append(match)

    return to_create, skipped


def save_matches(to_create):
    """
    Inserts the matches and rebuilds every rating once.

    Returns (created, replayed).

    bulk_create bypassing Match.save() is what makes this affordable:
    save() recomputes per match, so N imported matches would mean N replays
    of the full history. One recompute at the end gives the same ratings,
    and covers a file that is not in chronological order, since the replay
    always runs in (date, id) order.

    The insert and the recompute share a transaction, so a failure cannot
    leave stored matches whose results were never applied to any rating.
    """
    from ratings.services import recompute_all_ratings

    with transaction.atomic():
        Match.objects.bulk_create(to_create, batch_size=500)
        replayed = recompute_all_ratings()
    return len(to_create), replayed
