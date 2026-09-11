import { describe, expect, it } from 'vitest';
import { parseHeadToHead, parseMatchDetail } from './api';

const rating = { rating_before: 1200, rating_after: 1216, change: 16, direction: 'up' };

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
  player1_rating: rating,
  player2_rating: null,
};

describe('parseMatchDetail', () => {
  it('accepts a valid match with or without rating annotations', () => {
    expect(parseMatchDetail(match)).toEqual(match);
    expect(parseMatchDetail({ ...match, player2_rating: rating }).player2_rating).toEqual(rating);
  });

  it('rejects malformed payloads', () => {
    expect(() => parseMatchDetail(null)).toThrow();
    expect(() => parseMatchDetail({ ...match, player1_name: 12 })).toThrow();
    expect(() => parseMatchDetail({ ...match, date: 'not a date' })).toThrow();
    expect(() => parseMatchDetail({ ...match, player1_rating: { rating_before: 1200 } })).toThrow();
    expect(() => parseMatchDetail({ ...match, player1_rating: { ...rating, direction: 'sideways' } })).toThrow();
  });
});

describe('parseHeadToHead', () => {
  it('parses the global record and the match page', () => {
    expect(parseHeadToHead({
      record: { player1_wins: 2, player2_wins: 5 },
      count: 7,
      next: 'http://localhost/api/matches/7/head-to-head/?page=2',
      previous: null,
      results: [match],
    })).toEqual({
      record: { player1_wins: 2, player2_wins: 5 },
      count: 7,
      next: 'http://localhost/api/matches/7/head-to-head/?page=2',
      previous: null,
      results: [match],
    });
  });

  it('rejects bad records, counts, or rows', () => {
    expect(() => parseHeadToHead({
      record: { player1_wins: 'x', player2_wins: 1 }, count: 1, next: null, previous: null, results: [],
    })).toThrow();
    expect(() => parseHeadToHead({
      record: { player1_wins: 1, player2_wins: 1 }, count: -1, next: null, previous: null, results: [],
    })).toThrow();
    expect(() => parseHeadToHead({
      record: { player1_wins: 1, player2_wins: 1 }, count: 1, next: null, previous: null, results: [{}],
    })).toThrow();
  });
});
