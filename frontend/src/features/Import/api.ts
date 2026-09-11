import { record } from '../../services/api';

export interface SkippedRow { line: number; reason: string }
export interface PlayerPreviewRow { name: string; rating: number }
export interface MatchPreviewRow { player1: string; player2: string; score1: number; score2: number; date: string }
export type PreviewRow = PlayerPreviewRow | MatchPreviewRow;
export interface PreviewPayload { filename: string; rows: PreviewRow[]; skipped: SkippedRow[] }

export function parseSkipped(value: unknown): SkippedRow[] {
  if (!Array.isArray(value)) throw new Error('The API did not return skipped rows.');
  return value.map((row) => {
    if (!record(row) || !Number.isInteger(row.line) || typeof row.reason !== 'string') {
      throw new Error('The API did not return skipped rows.');
    }
    return { line: row.line as number, reason: row.reason };
  });
}

export function parsePlayerRow(value: unknown): PlayerPreviewRow {
  if (!record(value) || typeof value.name !== 'string' || !Number.isInteger(value.rating)) {
    throw new Error('The API did not return the import preview.');
  }
  return { name: value.name, rating: value.rating as number };
}

export function parseMatchRow(value: unknown): MatchPreviewRow {
  if (!record(value) || typeof value.player1 !== 'string' || typeof value.player2 !== 'string'
    || !Number.isInteger(value.score1) || !Number.isInteger(value.score2)
    || typeof value.date !== 'string' || !Number.isFinite(Date.parse(value.date))) {
    throw new Error('The API did not return the import preview.');
  }
  return {
    player1: value.player1, player2: value.player2,
    score1: value.score1 as number, score2: value.score2 as number, date: value.date,
  };
}

export function parsePreview(value: unknown, kind: 'players' | 'matches'): PreviewPayload {
  if (!record(value) || typeof value.filename !== 'string' || !Array.isArray(value.rows)) {
    throw new Error('The API did not return an import preview.');
  }
  return {
    filename: value.filename,
    rows: kind === 'players'
      ? value.rows.map(parsePlayerRow)
      : value.rows.map(parseMatchRow),
    skipped: parseSkipped(value.skipped),
  };
}
