import { describe, expect, it } from 'vitest';
import { parsePlayers } from './api';

const alice = { id: 1, name: 'Alice', display_rating: 1216, rank: 1, wins: 3, losses: 1 };
const ben = { id: 2, name: 'Ben', display_rating: 1184, rank: 2, wins: 1, losses: 3 };

describe('parsePlayers', () => {
  it('accepts a valid roster, including an empty one', () => {
    expect(parsePlayers([alice, ben])).toEqual([alice, ben]);
    expect(parsePlayers([])).toEqual([]);
  });

  it('rejects non-arrays and malformed rows', () => {
    expect(() => parsePlayers(null)).toThrow();
    expect(() => parsePlayers([{ ...alice, rank: '1' }])).toThrow();
    expect(() => parsePlayers([{ ...alice, display_rating: 'high' }])).toThrow();
    expect(() => parsePlayers([{ ...alice, id: 1.5 }])).toThrow();
  });
});
