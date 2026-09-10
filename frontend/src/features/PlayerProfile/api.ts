import type { PlayerProfile, RatingPoint } from '../../types/profile';

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function ratingPoint(value: unknown): value is RatingPoint {
  return record(value) && Number.isInteger(value.match) && typeof value.date === 'string'
    && Number.isFinite(Date.parse(value.date)) && typeof value.rating === 'number' && Number.isFinite(value.rating);
}

export function parseProfile(value: unknown): PlayerProfile {
  if (!record(value) || !Number.isInteger(value.id) || typeof value.name !== 'string'
    || typeof value.style !== 'string' || typeof value.grip !== 'string'
    || typeof value.created_date !== 'string' || !Number.isFinite(Date.parse(value.created_date))
    || typeof value.display_rating !== 'number' || typeof value.initial_rating !== 'number'
    || !Number.isInteger(value.rank) || !Number.isInteger(value.wins) || !Number.isInteger(value.losses)
    || !Number.isInteger(value.total_matches) || typeof value.highest_rating !== 'number'
    || !(value.win_percentage === null || typeof value.win_percentage === 'number')
    || typeof value.history_start !== 'string' || typeof value.history_end !== 'string'
    || typeof value.history_complete !== 'boolean'
    || !Array.isArray(value.rating_history) || !value.rating_history.every(ratingPoint)) {
    throw new Error('The API did not return a player profile. The backend must include the profile update.');
  }
  return value as unknown as PlayerProfile;
}

export function profilePath(playerId: number) {
  return `/api/players/${playerId}/profile/`;
}

export function playerMatchesPath(playerId: number, page: number) {
  return `/api/players/${playerId}/matches/?page=${page}`;
}
