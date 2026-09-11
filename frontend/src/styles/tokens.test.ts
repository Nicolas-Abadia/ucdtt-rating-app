import { describe, expect, it } from 'vitest';
import { AVATAR_COLORS, nameColorIndex } from './tokens';

describe('nameColorIndex', () => {
  it('is deterministic and always inside the palette', () => {
    expect(nameColorIndex('Alice')).toBe(nameColorIndex('Alice'));
    for (const name of ['Alice', 'Ben', 'officer', '']) {
      expect(nameColorIndex(name)).toBeGreaterThanOrEqual(0);
      expect(nameColorIndex(name)).toBeLessThan(AVATAR_COLORS.length);
    }
  });

  it('spreads different names across the palette', () => {
    const indexes = new Set(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'].map(nameColorIndex));
    expect(indexes.size).toBeGreaterThan(1);
  });
});
