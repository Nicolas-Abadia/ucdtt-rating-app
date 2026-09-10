import type { MatchRating } from '../types/match';
import styles from './RatingChange.module.css';

// Shared rating delta with directional arrow and color. Used by MatchCard
// lists and the match-detail participant cards, so the treatment stays
// identical everywhere.
export default function RatingChange({ rating }: { rating: MatchRating | null }) {
  if (!rating) return <span className={styles.unavailable}>Rating unavailable</span>;
  const signedChange = `${rating.change > 0 ? '+' : ''}${rating.change}`;
  const description = `Rating before ${rating.rating_before}, change ${signedChange}, rating after ${rating.rating_after}`;
  return (
    <span className={styles.rating} role="img" aria-label={description} title={description}>
      <span aria-hidden="true">{rating.rating_before}</span>
      <span aria-hidden="true" className={styles[rating.direction]}>
        {signedChange}{rating.change > 0 ? ' ▲' : rating.change < 0 ? ' ▼' : ''}
      </span>
    </span>
  );
}
