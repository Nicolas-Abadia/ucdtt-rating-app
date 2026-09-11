import { describe, expect, it } from 'vitest';
import { parsePreview, parseSkipped } from './api';

describe('parseSkipped', () => {
  it('parses skipped rows with line numbers', () => {
    expect(parseSkipped([{ line: 4, reason: 'No player named "Mystery".' }]))
      .toEqual([{ line: 4, reason: 'No player named "Mystery".' }]);
    expect(parseSkipped([])).toEqual([]);
  });

  it('rejects malformed rows', () => {
    expect(() => parseSkipped(null)).toThrow();
    expect(() => parseSkipped([{ line: '4', reason: 'x' }])).toThrow();
  });
});

describe('parsePreview', () => {
  it('parses player previews', () => {
    expect(parsePreview({
      filename: 'roster.csv',
      rows: [{ name: 'Alice', rating: 1350 }],
      skipped: [],
    }, 'players')).toEqual({ filename: 'roster.csv', rows: [{ name: 'Alice', rating: 1350 }], skipped: [] });
  });

  it('parses match previews', () => {
    const rows = [{ player1: 'Alice', player2: 'Ben', score1: 11, score2: 7, date: '2026-08-20T19:30:00-03:00' }];
    expect(parsePreview({ filename: 'matches.csv', rows, skipped: [] }, 'matches').rows).toEqual(rows);
  });

  it('rejects malformed envelopes and invalid rows', () => {
    expect(() => parsePreview({ rows: [], skipped: [] }, 'players')).toThrow();
    expect(() => parsePreview({ filename: 'x.csv', rows: 'oops', skipped: [] }, 'players')).toThrow();
    expect(() => parsePreview(
      { filename: 'x.csv', rows: [{ name: 'Alice', rating: 'soon' }], skipped: [] }, 'players',
    )).toThrow();
    expect(() => parsePreview(
      { filename: 'x.csv', rows: [{ player1: 'A', player2: 'B', score1: 11, score2: 7, date: 'yesterday' }], skipped: [] },
      'matches',
    )).toThrow();
  });
});
