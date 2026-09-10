# Match History implementation

## Scope

- Public read-only Match History at `/#matches`; Leaderboard at `/#leaderboard`.
- Hash routing keeps refresh and Back/Forward compatible with the static Vercel host without another dependency or rewrite.
- The existing header, account menu, navigation disclosure, device dark mode, reduced-motion handling, spacing, and desktop density remain shared.
- Reusable `components/MatchCard`, `SearchField`, `PageLayout`, and `RequestState`; page state, API validation, and the list live in `features/MatchHistory`. Shared payload types live in `types/match.ts`.
- Matches are grouped under device-local calendar-date headings. Cards show only the time and match ID in their metadata, plus edge scores, pre-match ratings, signed changes, and nonzero direction triangles. Names and ratings align inward: left participant right-aligned, right participant left-aligned. Missing rating history is explicit. A date heading repeats on the next page if that day's matches cross the pagination boundary; backend chronological order is preserved.
- Search uses player names or bare match IDs: `42` selects match 42, with `#42` accepted when copied from a card. Numeric player-ID search remains on the Leaderboard. The date picker has no visible label but retains an accessible name. It filters whole days, not exact hours. It combines with search, and either change resets pagination. Search and date filters apply to the complete backend queryset before pagination, not just the visible page. Clear filters resets both. Dates and times use the device timezone. Search is debounced 250ms; requests cancel on filter/page change or unmount, with stale responses ignored. Retry, empty, timeout, and invalid backend-payload states are included.
- Public navigation contains only Leaderboard and Match History, with matching outer corner radii. The selected underline is removed while aria-current and keyboard focus styling remain. Officer options are gated by an explicit isOfficer prop, default false; React authentication is not yet connected, so the current app always uses the public variant. The prepared officer variant retains disabled Log new match and Import CSV controls. Auth, React match detail, and write flows remain separate work. Cards are articles, not dead links.
- Leaderboard cards show a small #player ID below the name, separate from rank. Rank is vertically centered against the complete name/ID block. Match-card zero deltas show just 0, without an equals sign; nonzero deltas retain direction triangles.

## API

`GET /api/matches/?include=card&page=1`

Preserves the existing paginated envelope (`count`, `next`, `previous`, `results`), 20 rows per page, ordered by descending `(date, pk)`.

The ordinary list serializer remains unchanged. Opt-in cards add `player1_name`, `player2_name`, `player1_rating`, and `player2_rating` to existing summary fields. Each rating is null or:

```json
{"rating_before":1200,"rating_after":1216,"change":16,"direction":"up"}
```

`direction` is `up`, `down`, or `unchanged`. Ratings come from persisted RatingHistory, ordered by match chronology rather than history write time. Display values use Python rounding, like Player.display_rating. Change is the difference between displayed endpoints; no client-side Elo calculation or per-card detail requests.

The prior history row must correspond to the immediately preceding match. Otherwise the rating summary is null, not a substitute from an older row. Initial rating is used only before the first match. GET does not replay ratings or write to the database.

`q` retains player name/ID semantics at the API level, while the Match History UI routes bare numbers to `match_id`. `match_id` is an exact filter, composable with `q` and `date`. When `date` is selected, the frontend also sends `tz` as an IANA timezone. The backend filters in that zone, including daylight-saving boundaries. Omitting `tz` preserves the original API timezone behavior; an invalid timezone with a valid date returns 400. Malformed/out-of-range exact IDs return an empty list. Match detail retains `rating_changes`, and embedded player match lists remain compact.

## Deployment and validation

The backend update must be present before the frontend can load cards. Existing `VITE_API_BASE_URL` and backend CORS configuration remain in use. No new environment variables, database migrations, or runtime dependencies are required.

Run from the repository root with the normal development environment:

```bash
python manage.py test
cd frontend
npm run build
npm run lint
```

`players/test_match_cards.py` covers optional/default/detail contracts, chronology, replay after edit/backdate/delete, missing histories, ID search, pagination, and bounded serialization query count.

Implementation-time checks: isolated esbuild syntax checks passed for the five MatchHistory feature files and MatchCard; query/payload helper assertions and MatchCard static-render assertions passed. The backend annotation helper passed Python syntax parsing. These checks used copied source in a separate sandbox, not the repository's runtime environment. The project TypeScript/Vite build, ESLint, Django test suite, and browser layout checks have not been run.

Browser checks still required:

- Desktop and mobile, light and dark, reduced motion.
- Direct `/#matches` refresh and Back/Forward navigation.
- Long names, empty history, unmatched search, offline/retry, and multiple pages.
- Rapid search/date changes never showing the previous filter's results.
- Bare numeric match-ID search, combined name/date filters, local-midnight and daylight-saving boundaries, and Clear filters.
- Public dock has two destinations and no options toggle; the prepared officer variant appears only when explicitly supplied a confirmed auth state.
- Header and dock outside-tap/Escape behavior, including switching pages while the dock is hovered.
- Compare the card layout against the saved Match History design reference. Fresh live Figma extraction was unavailable during implementation, so pixel parity is not yet verified.
