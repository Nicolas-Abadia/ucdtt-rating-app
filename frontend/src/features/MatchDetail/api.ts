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

export function parseMatchDetail(value: unknown): MatchSummary {
  if (!record(value) || !Number.isInteger(value.id) || !Number.isInteger(value.player1) || !Number.isInteger(value.player2)
    || !Number.isInteger(value.score1) || !Number.isInteger(value.score2)
    || typeof value.player1_name !== 'string' || typeof value.player2_name !== 'string'
    || typeof value.date !== 'string' || !Number.isFinite(Date.parse(value.date))
    || !rating(value.player1_rating) || !rating(value.player2_rating)) {
    throw new Error('The API did not return match detail. The backend must include the detail update.');
  }
  return value as unknown as MatchSummary;
}

export interface MatchRecord { player1_wins: number; player2_wins: number }
export interface HeadToHeadPage extends MatchPage { record: MatchRecord }

export function parseHeadToHead(value: unknown): HeadToHeadPage {
  if (!record(value) || !record(value.record)
    || typeof value.record.player1_wins !== 'number' || typeof value.record.player2_wins !== 'number'
    || !Number.isInteger(value.count) || Number(value.count) < 0
    || !(value.next === null || typeof value.next === 'string')
    || !(value.previous === null || typeof value.previous === 'string')
    || !Array.isArray(value.results)) {
    throw new Error('The API did not return head-to-head data.');
  }
  return {
    count: value.count as number,
    next: value.next as string | null,
    previous: value.previous as string | null,
    results: value.results.map(parseMatchDetail),
    record: value.record as MatchRecord,
  };
}

export function matchDetailPath(matchId: number) {
  return `/api/matches/${matchId}/?include=card`;
}

export function headToHeadPath(matchId: number, page: number) {
  return `/api/matches/${matchId}/head-to-head/?page=${page}`;
}
