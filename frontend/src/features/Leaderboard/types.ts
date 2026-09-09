// Shapes mirroring the DRF API responses for the Leaderboard feature.

export interface PlayerData {
  id: number;
  name: string;
  display_rating: number;
  rank: number;
  wins: number;
  losses: number;
}

export interface DRFResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[]; // The actual array lives here!
}
