import { getJson } from '../../services/api';
import type { MatchPage, MatchRating, MatchSummary } from '../../types/match';

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function rating(value: unknown): value is MatchRating | null {
  return value === null || (record(value)
    && typeof value.rating_before === 'number' && Number.isFinite(value.rating_before)
    && typeof value.rating_after === 'number' && Number.isFinite(value.rating_after)
    && typeof value.change === 'number' && Number.isFinite(value.change)
    && ['up', 'down', 'unchanged'].includes(String(value.direction)));
}

function match(value: unknown): value is MatchSummary {
  return record(value)
    && Number.isInteger(value.id) && Number.isInteger(value.player1) && Number.isInteger(value.player2)
    && Number.isInteger(value.score1) && Number.isInteger(value.score2)
    && typeof value.player1_name === 'string' && typeof value.player2_name === 'string'
    && typeof value.date === 'string' && Number.isFinite(Date.parse(value.date))
    && rating(value.player1_rating) && rating(value.player2_rating);
}

export function parseMatchPage(value: unknown): MatchPage {
  if (!record(value) || !Number.isInteger(value.count) || Number(value.count) < 0
    || !(value.next === null || typeof value.next === 'string')
    || !(value.previous === null || typeof value.previous === 'string')
    || !Array.isArray(value.results) || !value.results.every(match)) {
    throw new Error('The API did not return match-card data. The backend must include the Match History update.');
  }
  return value as unknown as MatchPage;
}

export function matchListPath(query: string, page: number, date = '') {
  const params = new URLSearchParams({ include: 'card', page: String(page) });
  const value = query.trim();
  // Bare numbers are match IDs here; the leaderboard searches player IDs.
  // Accept a copied #ID too, but never require the prefix.
  if (/^\d+$/.test(value)) params.set('match_id', value);
  else if (value.startsWith('#')) params.set('match_id', value.slice(1).trim() || 'invalid');
  else if (value) params.set('q', value);
  if (date) {
    params.set('date', date);
    params.set('tz', Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');
  }
  return `/api/matches/?${params}`;
}

export async function fetchMatches(query: string, page: number, signal: AbortSignal, date = '') {
  return parseMatchPage(await getJson(matchListPath(query, page, date), signal));
}
