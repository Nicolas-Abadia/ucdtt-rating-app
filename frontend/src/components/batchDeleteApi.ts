import { record } from '../services/api';
import { parseMatchDetail } from '../features/MatchDetail/api';
import type { MatchSummary } from '../types/match';

export interface SkippedItem { id: number; name?: string; reason: string }
export interface BatchResult { deleted: number; skipped: SkippedItem[] }

export function parseMatchCardPage(value: unknown): { next: string | null; results: MatchSummary[] } {
  if (!record(value) || !(value.next === null || typeof value.next === 'string') || !Array.isArray(value.results)) {
    throw new Error('The API did not return matches.');
  }
  return { next: value.next as string | null, results: value.results.map(parseMatchDetail) };
}

export function parseBatchResult(value: unknown): BatchResult {
  if (!record(value) || !Array.isArray(value.deleted) || !Array.isArray(value.skipped)) {
    throw new Error('The API did not return the delete result.');
  }
  const skipped: SkippedItem[] = [];
  for (const row of value.skipped) {
    if (!record(row) || !Number.isInteger(row.id) || typeof row.reason !== 'string') {
      throw new Error('The API did not return the delete result.');
    }
    skipped.push({
      id: row.id as number,
      name: typeof row.name === 'string' ? row.name : undefined,
      reason: row.reason,
    });
  }
  return { deleted: value.deleted.length, skipped };
}
