import { describe, expect, it } from 'vitest';
import { messageFrom, record } from './api';

describe('record', () => {
  it('accepts objects and rejects everything else', () => {
    expect(record({})).toBe(true);
    expect(record([])).toBe(true);
    expect(record(null)).toBe(false);
    expect(record('x')).toBe(false);
    expect(record(42)).toBe(false);
  });
});

describe('messageFrom', () => {
  it('returns strings as-is', () => {
    expect(messageFrom('One player must win.')).toBe('One player must win.');
  });

  it('flattens DRF arrays, including nested ones', () => {
    expect(messageFrom(['One player must win.'])).toBe('One player must win.');
    expect(messageFrom(['First.', ['Second.']])).toBe('First. Second.');
  });

  it('returns null for shapes that carry no message', () => {
    expect(messageFrom(42)).toBeNull();
    expect(messageFrom(null)).toBeNull();
    expect(messageFrom([])).toBeNull();
    expect(messageFrom([42])).toBeNull();
  });
});
