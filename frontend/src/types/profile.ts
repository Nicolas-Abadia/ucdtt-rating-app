export interface RatingPoint {
  match: number;
  date: string;
  rating: number;
}

export interface PlayerProfile {
  id: number;
  name: string;
  style: string;
  grip: string;
  created_date: string;
  display_rating: number;
  initial_rating: number;
  rank: number;
  wins: number;
  losses: number;
  total_matches: number;
  highest_rating: number;
  win_percentage: number | null;
  history_start: string;
  history_end: string;
  history_complete: boolean;
  rating_history: RatingPoint[];
}
