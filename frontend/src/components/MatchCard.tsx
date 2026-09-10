import type { MatchSummary } from '../types/match';
import RatingChange from './RatingChange';
import styles from './MatchCard.module.css';

const matchTime = new Intl.DateTimeFormat(undefined, {
  hour: 'numeric', minute: '2-digit',
});

// Shared by match lists, player history, and head-to-head lists. `href`
// makes the whole card a real link to the match detail route; the article
// itself holds no other interactive elements, so no nested-link violation.
interface MatchCardProps {
  match: MatchSummary;
  variant?: 'gold' | 'blue';
  href?: string;
}

export default function MatchCard({ match, variant = 'gold', href }: MatchCardProps) {
  const firstWon = match.score1 > match.score2;
  const card = (
    <article className={`${styles.card} ${variant === 'blue' ? styles.blue : ''}`} aria-label={`Match ${match.id}: ${match.player1_name} versus ${match.player2_name}`}>
      <span className={`${styles.score} ${firstWon ? styles.winner : ''}`}
        aria-label={`${match.player1_name}: ${match.score1}${firstWon ? ', winner' : ''}`}>{match.score1}</span>
      <div className={styles.body}>
        <div className={styles.meta}>
          <span>#{match.id}</span>
          <time dateTime={match.date} title={new Date(match.date).toLocaleString()}>{matchTime.format(new Date(match.date))}</time>
        </div>
        <div className={styles.players}>
          <div className={styles.player}>
            <span className={styles.name} title={match.player1_name}>{match.player1_name}</span>
            <RatingChange rating={match.player1_rating} />
          </div>
          <div className={styles.player}>
            <span className={styles.name} title={match.player2_name}>{match.player2_name}</span>
            <RatingChange rating={match.player2_rating} />
          </div>
        </div>
      </div>
      <span className={`${styles.score} ${!firstWon ? styles.winner : ''}`}
        aria-label={`${match.player2_name}: ${match.score2}${!firstWon ? ', winner' : ''}`}>{match.score2}</span>
    </article>
  );
  if (!href) return card;
  return <a href={href} className={styles.cardLink}>{card}</a>;
}
