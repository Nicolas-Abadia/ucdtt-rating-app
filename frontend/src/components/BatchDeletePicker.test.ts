import { describe, expect, it } from 'vitest';
import { parseBatchResult, parseMatchCardPage } from './batchDeleteApi';

const match = {
  id: 7,
  url: 'http://localhost/api/matches/7/',
  player1: 1,
  player2: 2,
  score1: 11,
  score2: 7,
  player1_name: 'Alice',
  player2_name: 'Ben',
  date: '2026-09-10T20:00:00Z',
  player1_rating: null,
  player2_rating: null,
};

describe('parseBatchResult', () => {
  it('counts deletions and parses skipped rows', () => {
    expect(parseBatchResult({
      deleted: [{ id: 1, name: 'Alice' }, { id: 2 }],
      skipped: [{ id: 3, name: 'Ben', reason: 'Has recorded matches and cannot be deleted.' }],
    })).toEqual({
      deleted: 2,
      skipped: [{ id: 3, name: 'Ben', reason: 'Has recorded matches and cannot be deleted.' }],
    });
  });

  it('tolerates nameless skipped rows and rejects bad shapes', () => {
    expect(parseBatchResult({ deleted: [], skipped: [{ id: 9, reason: 'Gone.' }] }).skipped)
      .toEqual([{ id: 9, name: undefined, reason: 'Gone.' }]);
    expect(() => parseBatchResult({ deleted: [], skipped: [{ reason: 'x' }] })).toThrow();
    expect(() => parseBatchResult(null)).toThrow();
  });
});

describe('parseMatchCardPage', () => {
  it('parses a paginated card page', () => {
    expect(parseMatchCardPage({ next: null, results: [match] })).toEqual({ next: null, results: [match] });
    expect(parseMatchCardPage({ next: 'http://localhost/api/matches/?page=2', results: [] }).next)
      .toBe('http://localhost/api/matches/?page=2');
  });

  it('rejects bad pages', () => {
    expect(() => parseMatchCardPage({ next: 2, results: [] })).toThrow();
    expect(() => parseMatchCardPage({ next: null, results: [{}] })).toThrow();
  });
});
