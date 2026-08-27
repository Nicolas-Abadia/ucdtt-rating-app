# UCDTT Rating App v1 (Under Development)

![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![Django](https://img.shields.io/badge/django-6.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

UC Davis Table Tennis Club internal rating system.

**Live app: <https://ucdtt-rating-app.onrender.com>**

> Hosted on Render's free tier, which spins the service down after roughly 15 minutes of inactivity. The first request after a quiet period takes about 50 seconds while the service wakes up. Everything after that is fast.

## What it does

- Tracks players and their ratings.
- Records match results.
- Updates ratings after each match using an Elo-style system.
- Supports full recomputation from match history when a result needs correction.
- Automatically replays affected ratings when a match is backdated, edited, or deleted.
- Imports players and match history in bulk from CSV, from the browser or the command line.
- Displays every date and time in the viewer's own timezone.
- Lets a signed-in officer change their own username and password.

## Tech stack

- Django 6.0.7
- PostgreSQL — 16 locally via Docker, Neon in production
- Python 3.13
- `dj-database-url` for database configuration
- `gunicorn` as the WSGI server, `whitenoise` for static file serving
- Deployed on Render, with Neon as the managed Postgres host

## Local setup

1. Clone the repo and create a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the local PostgreSQL container:
   ```bash
   docker compose up -d
   ```
4. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
5. Generate a secret key and paste it into `DJANGO_SECRET_KEY` in `.env`. The example file ships with an empty value, and Django will not start without one:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
6. Run migrations:
   ```bash
   python manage.py migrate
   ```
7. Create an admin user:
   ```bash
   python manage.py createsuperuser
   ```
8. Run the server:
   ```bash
   python manage.py runserver
   ```

## Running tests

```bash
python manage.py test
```

## Rating system

Ratings are updated once per match using a zero-sum Elo calculation.

Expected score for player A against player B:

```
E_a = 1 / (1 + 10^((R_b - R_a) / 400))
```

Rating update for player A after the match:

```
R_a' = R_a + K * (S_a - E_a)
```

Where:

- `R_a` is the current rating of player A
- `R_b` is the current rating of player B
- `E_a` is the expected score (between 0 and 1)
- `S_a` is the actual result: 1 for a win, 0 for a loss
- `K` is the sensitivity constant

Parameters used in this app:

- `K = 32`
- Starting rating for an unknown player: 1200
- New players may be seeded with an arbitrary `initial_rating` (e.g., borrowed from USATT rankings).
- A `recompute_ratings` management command resets every player to their `initial_rating` and replays all matches in chronological order, making it easy to correct bad entries.

## Management commands

### `recompute_ratings`

Resets every player to their `initial_rating` and replays all matches in chronological order.

```bash
python manage.py recompute_ratings
```

This is not normally needed. `Match.save()` and `Match.delete()` already trigger a replay whenever a match is backdated, edited, or removed. Run it manually after any bulk write that bypasses `save()`, such as a `bulk_create` of matches or a `queryset.update()`.

### `import_players`

Bulk-creates players from a CSV. The `name` column is required; `rating` is optional and defaults to 1200.

```csv
name,rating
Alice Chen,1450
Bob Rivera,
Carla Diaz,1180
```

```bash
python manage.py import_players roster.csv --dry-run   # report only, writes nothing
python manage.py import_players roster.csv             # write
```

Always run `--dry-run` first. It prints the target database and every row it would skip.

### `import_matches`

Bulk-creates matches from a CSV. All five columns are required. Players are resolved by name, case-insensitively, and are never created implicitly, so import the roster first.

```csv
player1,player2,score1,score2,date
Alice Chen,Bob Rivera,11,7,2026-08-20 19:30
Carla Diaz,Alice Chen,9,11,2026-08-21
```

```bash
python manage.py import_matches matches.csv --dry-run   # report only, writes nothing
python manage.py import_matches matches.csv             # write
```

Dates accept `YYYY-MM-DD HH:MM` or a bare `YYYY-MM-DD`, which is read as midnight. A timestamp with no UTC offset is interpreted in `settings.TIME_ZONE`, which the command prints before writing; include an offset such as `2026-08-20T19:30-03:00` to remove the ambiguity.

The file does not need to be in chronological order. Matches are inserted with `bulk_create` and ratings are rebuilt once at the end by a single `recompute_all_ratings()` call inside the same transaction, rather than replaying the whole history once per row. Because `bulk_create` skips `save()` and `full_clean()`, every rule the match form enforces (distinct players, non-negative scores, no ties, no future dates, no duplicates) is checked in Python first. Offending rows are skipped and reported by line number instead of rolling back the entire file.

## CSV imports from the browser

Officers can upload the same files from the app, so a roster or backfill no longer requires a local checkout:

| Page | URL |
| --- | --- |
| Import players | `/import_players/` |
| Import matches | `/matches/import_matches/` |

Both pages sit behind an Import CSV button next to Add new player and Add new match, and both require login. Parsing, validation, and the rating rebuild are shared with the management commands through `players/imports.py`, so the same file produces the same result either way. Preview only is checked by default: the first upload reports what would be created and what would be skipped, and writes nothing. Uploads must end in `.csv` and are capped at 2 MB. One difference from the commands: a timestamp with no offset is read in the uploader's own timezone rather than `settings.TIME_ZONE`.

## Running management commands against production

Neon accepts connections from anywhere, so production maintenance runs from a local checkout.

Keep the production connection string in `.neon-prod-url`, which is gitignored, and pass it inline:

```bash
source .venv/bin/activate
DATABASE_URL="$(cat .neon-prod-url)" python manage.py import_players roster.csv --dry-run
DATABASE_URL="$(cat .neon-prod-url)" python manage.py import_matches matches.csv --dry-run
```

## Deployment

Runs as a Render web service backed by a Neon Postgres database.

- Build: `pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate`
- Start: `gunicorn config.wsgi:application`
- Static files are served by WhiteNoise from the application process, so no CDN or storage bucket is required.

Required environment variables:

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Cryptographic signing key for sessions and CSRF tokens |
| `DJANGO_DEBUG` | `False` in production |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames, no scheme or trailing slash |
| `DATABASE_URL` | Postgres connection string, pooled and with `sslmode=require` |

Setting `DJANGO_DEBUG=False` also switches on HTTPS redirects, secure cookies, HSTS, and the hashed-manifest static storage backend.

## Project structure

- `config/` — Django settings and URL routing
- `players/` — Players, matches, rating history, views, and management commands
- `ratings/` — Pure Elo math and rating service layer

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
