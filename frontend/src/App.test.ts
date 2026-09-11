import { describe, expect, it } from 'vitest';
import { parseRoute } from './router';

describe('parseRoute', () => {
  it('defaults to the leaderboard', () => {
    expect(parseRoute('')).toEqual({ name: 'leaderboard' });
    expect(parseRoute('#')).toEqual({ name: 'leaderboard' });
    expect(parseRoute('#leaderboard')).toEqual({ name: 'leaderboard' });
  });

  it('parses the match routes', () => {
    expect(parseRoute('#matches')).toEqual({ name: 'matches' });
    expect(parseRoute('#matches/42')).toEqual({ name: 'match', id: 42 });
    expect(parseRoute('#matches/new')).toEqual({ name: 'match-new' });
    expect(parseRoute('#matches/42/edit')).toEqual({ name: 'match-edit', id: 42 });
  });

  it('parses the player routes', () => {
    expect(parseRoute('#players/3')).toEqual({ name: 'player', id: 3 });
    expect(parseRoute('#players/new')).toEqual({ name: 'player-new' });
    expect(parseRoute('#players/3/edit')).toEqual({ name: 'player-edit', id: 3 });
  });

  it('parses the import and login routes', () => {
    expect(parseRoute('#import')).toEqual({ name: 'import', kind: 'players' });
    expect(parseRoute('#import/matches')).toEqual({ name: 'import', kind: 'matches' });
    expect(parseRoute('#login')).toEqual({ name: 'login' });
  });

  it('parses the officer creation route and rejects the bare section', () => {
    expect(parseRoute('#officers/new')).toEqual({ name: 'officer-new' });
    expect(parseRoute('#officers')).toEqual({ name: 'not-found' });
    expect(parseRoute('#account')).toEqual({ name: 'account' });
  });

  it('rejects malformed or unknown hashes', () => {
    expect(parseRoute('#matches/abc')).toEqual({ name: 'not-found' });
    expect(parseRoute('#matches/0')).toEqual({ name: 'not-found' });
    expect(parseRoute('#players/-1')).toEqual({ name: 'not-found' });
    expect(parseRoute('#matches/1/delete')).toEqual({ name: 'not-found' });
    expect(parseRoute('#import/teams')).toEqual({ name: 'not-found' });
    expect(parseRoute('#nope')).toEqual({ name: 'not-found' });
  });
});
