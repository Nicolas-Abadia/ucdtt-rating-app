import type { CSSProperties } from 'react';
import PageLayout from '../../components/PageLayout';
import RatingChange from '../../components/RatingChange';
import RequestState from '../../components/RequestState';
import ScopedMatchList from '../../components/ScopedMatchList';
import useApiResource from '../../services/useApiResource';
import { AVATAR_COLORS } from '../../styles/tokens';
import type { MatchRating } from '../../types/match';
import { headToHeadPath, matchDetailPath, parseHeadToHead, parseMatchDetail } from './api';
import styles from './MatchDetailPage.module.css';

const dateFormatter = new Intl.DateTimeFormat(undefined, { dateStyle: 'long' });
const timeFormatter = new Intl.DateTimeFormat(undefined, { timeStyle: 'short' });

export default function MatchDetailPage({ matchId }: { matchId: number }) {
  const { data: match, loading, error, notFound, retry } = useApiResource(matchDetailPath(matchId), parseMatchDetail);

  return (
    <PageLayout title="Match Detail" activePage="matches" backLabel="Back to match history" backHash="#matches"
      officerContext="match" officerResourceId={matchId}>
      {loading ? (
        <RequestState loading title="Loading match" message="The server may take a moment to respond." />
      ) : notFound ? (
        <RequestState title="Match not found" message={`No match exists with ID ${matchId}.`} />
      ) : error ? (
        <RequestState title="Unable to load match" message={error} onRetry={retry} />
      ) : match ? (
        <div className={styles.layout}>
          <div className={styles.mainColumn}>
            <div className={styles.participants}>
              <ParticipantCard slot="Player 1" name={match.player1_name} playerId={match.player1}
                score={match.score1} winner={match.score1 > match.score2} rating={match.player1_rating} />
              <ParticipantCard slot="Player 2" name={match.player2_name} playerId={match.player2}
                score={match.score2} winner={match.score2 > match.score1} rating={match.player2_rating} />
            </div>
            <section className={styles.dateSection} aria-label="Date and time">
              <h3 className={styles.sectionHeading}>Date and time</h3>
              <p className={styles.dateValue}>
                <time dateTime={match.date}>
                  {dateFormatter.format(new Date(match.date))} · {timeFormatter.format(new Date(match.date))}
                </time>
              </p>
            </section>
          </div>
          <div className={styles.sideColumn}>
            <ScopedMatchList
              title="Head-to-Head Record"
              emptyLabel="No prior meetings between these players."
              buildPath={(page) => headToHeadPath(matchId, page)}
              parse={parseHeadToHead}
              variant="blue"
              cardHref={(item) => `#matches/${item.id}`}
              renderSummary={(data) => (
                <span className={styles.record}>
                  {match.player1_name} {data.record.player1_wins} - {data.record.player2_wins} {match.player2_name}
                </span>
              )}
            />
          </div>
        </div>
      ) : null}
    </PageLayout>
  );
}

interface ParticipantCardProps {
  slot: string;
  name: string;
  playerId: number;
  score: number;
  winner: boolean;
  rating: MatchRating | null;
}

// Gold-bordered participant card per the Figma match-detail spec: avatar,
// name, UCDTTID with the number in daylight-sky-blue, and the shared
// rating-delta component. The whole card links to the player's profile.
function ParticipantCard({ slot, name, playerId, score, winner, rating }: ParticipantCardProps) {
  const colorIndex = playerId % AVATAR_COLORS.length;
  const avatarStyle = {
    '--avatar-bg': AVATAR_COLORS[colorIndex],
    '--avatar-ink': colorIndex >= 3 ? 'var(--tone-black)' : 'var(--white)',
  } as CSSProperties;
  return (
    <div className={styles.participantBlock}>
      <span className={styles.slot}>{slot}</span>
      <a href={`#players/${playerId}`} className={styles.participant} aria-label={`${slot}: ${name}, view player profile`}>
        <div className={styles.avatar} style={avatarStyle} aria-hidden="true">
          {name.trim().charAt(0).toUpperCase()}
        </div>
        <span className={styles.participantName}>{name}</span>
        <span className={styles.playerId}>ID: <span className={styles.ucdttId}>{playerId}</span></span>
        <RatingChange rating={rating} />
      </a>
      <div className={styles.scoreBlock}>
        <span className={styles.scoreLabel}>Score</span>
        <span className={`${styles.participantScore} ${winner ? styles.winner : ''}`}
          aria-label={`${name}: ${score}${winner ? ', winner' : ''}`}>{score}</span>
      </div>
    </div>
  );
}
