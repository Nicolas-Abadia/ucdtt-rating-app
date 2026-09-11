import { record } from '../../services/api';
import type { PlayerData } from './types';

// Shared roster parser: leaderboard page, match form picker, batch delete.
export function parsePlayers(value: unknown): PlayerData[] {
  if (!Array.isArray(value) || !value.every((player) => record(player)
    && Number.isInteger(player.id) && typeof player.name === 'string'
    && typeof player.display_rating === 'number' && Number.isFinite(player.display_rating)
    && Number.isInteger(player.rank) && Number.isInteger(player.wins) && Number.isInteger(player.losses))) {
    throw new Error('The API did not return the leaderboard.');
  }
  return value as PlayerData[];
}
