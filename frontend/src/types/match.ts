export interface MatchRating {
  rating_before: number;
  rating_after: number;
  change: number;
  direction: 'up' | 'down' | 'unchanged';
}

export interface MatchSummary {
  id: number;
  player1: number;
  player2: number;
  player1_name: string;
  player2_name: string;
  score1: number;
  score2: number;
  date: string;
  player1_rating: MatchRating | null;
  player2_rating: MatchRating | null;
}

export interface MatchPage {
  count: number;
  next: string | null;
  previous: string | null;
  results: MatchSummary[];
}
