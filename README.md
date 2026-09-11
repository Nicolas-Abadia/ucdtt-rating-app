# Table Tennis Rating App v1.5 (Under Development)

[![CI](https://github.com/Nicolas-Abadia/ucdtt-rating-app/actions/workflows/ci.yml/badge.svg)](https://github.com/Nicolas-Abadia/ucdtt-rating-app/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![Django](https://img.shields.io/badge/django-6.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

A reusable table tennis rating system currently being developed for the **Table Tennis Club at UC Davis**.

**Live app: <https://ucdtt-rating-app.onrender.com>**  
**Browsable API: <https://ucdtt-rating-app.onrender.com/api/>**

> Hosted on Render's free tier, which spins the service down after roughly 15 minutes of inactivity. The first request after a quiet period takes about 50 seconds while the service wakes up. Everything after that is fast.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/screenshots/v1/leaderboard-screenshot.png">
  <source media="(prefers-color-scheme: light)" srcset="docs/screenshots/v1/leaderboard-light-screenshot.png">
  <img alt="Leaderboard Screenshot" src="docs/screenshots/v1/leaderboard-screenshot.png">
</picture>

[Screenshots of every page](docs/screenshots/v1/README.md)

## What it does

- Tracks players and their ratings.
- Records match results.
- Updates ratings after each match using an Elo-style system.
- Supports full recomputation from match history when a result needs correction.
- Automatically replays affected ratings when a match is backdated, edited, or deleted.
- Imports players and match history in bulk from CSV, from the browser or the command line.
- Displays every date and time in the viewer's own timezone.
- Lets a signed-in officer change their own username and password.
- Lets officers log, edit, and delete matches, add, edit, and delete players, and bulk-import or bulk-delete both, from the React app or the server-rendered pages.
- Provides a public REST API for player and match data; officer-only write endpoints (create, update, delete, CSV import, batch delete) authenticate with JWT.

## Tech stack

- Django 6.0.7
- Django REST Framework 3.18
- PostgreSQL 16 locally via Docker; any compatible PostgreSQL host in production
- Python 3.13
- `dj-database-url` for database configuration
- `djangorestframework-simplejwt` for officer JWT auth
- `gunicorn` as the WSGI server, `whitenoise` for static file serving
- React and TypeScript frontend in `frontend/`, built with Vite, tested with Vitest

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

## REST API
Player and match data is exposed as JSON. Reads are public; writes are officer-only and authenticate with JWT (below). The API includes a browsable interface, so the public endpoints can be explored directly in a browser without a separate frontend.

| Resource | List endpoint | Detail endpoint |
| --- | --- | --- |
| Players | `/api/players/` | `/api/players/<id>/` |
| Matches | `/api/matches/` | `/api/matches/<id>/` |
| Leaderboard | `/api/leaderboard/` | Not applicable |

Player and match lists support player-name fragments or exact numeric player IDs with `?q=`:

```text
/api/players/?q=wang
/api/matches/?q=16
```

Match lists also support calendar-day filtering with `?date=YYYY-MM-DD`:

```text
/api/matches/?date=2026-08-20
```

Player and match lists use page-number pagination with 20 results per page. Match lists (including those embedded in player detail) contain match summaries; `rating_changes` is returned only by match detail. Player detail still includes the player's own `rating_history`.

`/api/leaderboard/` returns an unpaginated JSON array with exactly `id`, `name`, `rank`, `display_rating`, `wins`, and `losses`. Wins/losses are calculated from recorded match scores, including both player positions; no stored counters or migration are required. Rank uses the exact stored rating, with equal ratings sharing competition ranks (1, 1, 3). Name and ID provide stable ordering within ties. The React leaderboard filters this complete roster locally and preserves server ranks. This compact full-roster response suits a club-sized deployment; large deployments should introduce server-side search and pagination without recalculating ranks within each page.

Match endpoints accept `?include=card` to add the card annotations the React app renders (player names, wins/losses, and rating before/after each side). `/api/matches/<id>/head-to-head/` returns the pair's global record — counting every meeting, before and after the selected match — plus their paginated meetings newest first.

### Officer write endpoints

Officer writes authenticate with a bearer token: obtain with `POST /api/token/`, refresh with `POST /api/token/refresh/`, and revoke the refresh token on logout with `POST /api/token/blacklist/`. Access tokens live 30 minutes; refresh tokens rotate and are blacklisted on use.

| Operation | Endpoint |
| --- | --- |
| Create / update / delete a player | `POST /api/players/`, `PUT\|PATCH\|DELETE /api/players/<id>/` |
| Create / update / delete a match | `POST /api/matches/`, `PUT\|PATCH\|DELETE /api/matches/<id>/` |
| Preview or run a CSV import | `POST /api/players/import/`, `POST /api/matches/import/` |
| Delete many rows at once | `POST /api/players/batch-delete/`, `POST /api/matches/batch-delete/` with `{"ids": [...]}` |
| Create an officer account | `POST /api/officers/` |
| Change the signed-in officer's username or password | `POST /api/account/` |

Writes enforce the same rules as the HTML forms: distinct players, non-negative unequal scores, no future dates, and a case-insensitively unique player name. Editing or deleting a match replays the affected ratings. Deleting a player with recorded matches is refused with `409`, because their results feed everyone else's ratings. Creating an officer reuses the HTML signup's form, so the API applies the same username rules and the configured password validators; only a signed-in officer can create another. The account endpoint likewise reuses the HTML account page's forms: username and password changes are validated together before either writes, and a password change requires the current password.

Import endpoints take a multipart `csv_file`. The default response is a preview (`{"filename", "rows", "skipped", ...}`) that writes nothing; adding `?confirm=1` performs the import. Parsing, validation, and the single rating rebuild are shared with the management commands and the HTML importer through `players/imports.py`.

Batch delete removes the listed rows and never fails the whole batch over individual rows: players with recorded matches and unknown ids come back under `skipped` (`{"id", "name?", "reason"}`) while the rest are deleted. Match batches recompute ratings once after all deletions, like the CSV importer.

The server-rendered match list additionally supports an exact match-ID filter, separate from player search: `/matches/?match_id=42`. It combines with `q` and `date`; invalid or unknown IDs return no matches.

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

Both pages sit behind an Import CSV button next to Add new player and Add new match, and both require login. Parsing, validation, and the rating rebuild are shared with the management commands through `players/imports.py`, so the same file produces the same result either way.

The file is picked once. Uploading it writes nothing: it reports what would be created and what would be skipped, and offers Import and Discard. Confirming imports the file that was just previewed, without asking for it again. While the preview is on screen the file's text waits in the officer's session, keyed by a one-use token, so a refresh or a double click cannot import the same file twice, and a token from the roster importer cannot be confirmed through the match importer. Confirming re-reads the database rather than trusting the preview, so a row that another officer added in between is reported as skipped instead of written twice.

Uploads must end in `.csv` and are capped at 2 MB. One difference from the commands: a timestamp with no offset is read in the uploader's own timezone rather than `settings.TIME_ZONE`.

## Running management commands against production

Run maintenance from the deployment platform's secure shell/job runner, or from a local checkout only when the database's network policy permits it. Use the standard `DATABASE_URL` environment variable with the selected PostgreSQL provider's connection string.

For optional local maintenance, a connection string may be stored in `.production-database-url`, which is gitignored. Restrict access to that file and never commit its contents:

```bash
source .venv/bin/activate
chmod 600 .production-database-url
DATABASE_URL="$(cat .production-database-url)" python manage.py import_players roster.csv --dry-run
DATABASE_URL="$(cat .production-database-url)" python manage.py import_matches matches.csv --dry-run
```

Inspect the target database and dry-run report before a write. Existing credential files are not renamed automatically; legacy ignore rules remain to prevent accidental tracking.

## Deployment

Run the Django application on any compatible Python/WSGI host with a PostgreSQL database. Choose hosting, connection pooling, and network access policies independently.

- Build: `pip install -r requirements.txt && python manage.py collectstatic --no-input`
- Release: `python manage.py migrate`, run once before new application instances receive traffic. A platform without a release phase can run this after the build, with deployment concurrency controlled.
- Start: `gunicorn config.wsgi:application`
- Static files are served by WhiteNoise from the application process, so no CDN or storage bucket is required.

Required environment variables:

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Cryptographic signing key for sessions and CSRF tokens |
| `DJANGO_DEBUG` | `False` in production |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames, no scheme or trailing slash |
| `DATABASE_URL` | PostgreSQL connection string with the TLS options required by the selected host; use a pooling endpoint only when supported |

Setting `DJANGO_DEBUG=False` also switches on HTTPS redirects, secure cookies, HSTS, and the hashed-manifest static storage backend. The current proxy configuration expects a trusted TLS-terminating reverse proxy that strips client-supplied `X-Forwarded-Proto` headers and sets the correct value. Review this setting when deploying without that proxy arrangement.

### React frontend

The React app is the primary interface, deployed separately as a static build. It talks to this API with `VITE_API_BASE_URL` set to the backend origin at build time, and the backend's `CORS_ALLOWED_ORIGINS` lists the frontend's exact origin.

```bash
cd frontend
npm ci
npm run dev    # Vite dev server, proxies /api to the local Django server
npm run build  # type-check and production build into dist/
npm run lint   # ESLint
npm test       # Vitest parser and routing tests
```

It is a single-page app with hash routes, so the static host needs no rewrite rules. Public routes cover the leaderboard, match history, player profiles, and match detail. Officer routes — login, log/edit match, add/edit player, and the CSV import pages — sit behind the JWT session kept in localStorage. Single-record deletes happen inline from the navigation dock (a two-step red confirm), and the dock's Delete action opens a batch-delete picker for removing many players or matches at once. The write forms share one confirmation dock: disabled until the form is valid, a slow breathing glow in the flow's accent color (gold for matches, blue for players, purple for imports, red for deletes), and a red shake on validation errors.

## Project structure

- `config/` — Django settings and URL routing
- `players/` — Players, matches, rating history, views, and management commands
- `ratings/` — Pure Elo math and rating service layer
- `frontend/` — React + TypeScript single-page app (the primary interface)
- `docs/` — Screenshots of the deployed app

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
