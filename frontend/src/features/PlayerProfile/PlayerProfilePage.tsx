import type { CSSProperties } from 'react';
import PageLayout from '../../components/PageLayout';
import RequestState from '../../components/RequestState';
import ScopedMatchList from '../../components/ScopedMatchList';
import useApiResource from '../../services/useApiResource';
import { AVATAR_COLORS } from '../../styles/tokens';
import { parseMatchPage } from '../MatchHistory/api';
import { parseProfile, playerMatchesPath, profilePath } from './api';
import type { PlayerProfile } from '../../types/profile';
import RatingChart from './RatingChart';
import styles from './PlayerProfilePage.module.css';

const registeredFormatter = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' });

export default function PlayerProfilePage({ playerId }: { playerId: number }) {
  const { data: profile, loading, error, notFound, retry } = useApiResource(profilePath(playerId), parseProfile);

  return (
    <PageLayout title="Player Profile" activePage="leaderboard" backLabel="Back to leaderboard" backHash="#leaderboard" officerContext="player">
      {loading ? (
        <RequestState loading title="Loading player" message="The server may take a moment to respond." />
      ) : notFound ? (
        <RequestState title="Player not found" message={`No player exists with ID ${playerId}.`} />
      ) : error ? (
        <RequestState title="Unable to load player" message={error} onRetry={retry} />
      ) : profile ? (
        <ProfileContent profile={profile} playerId={playerId} />
      ) : null}
    </PageLayout>
  );
}

function ProfileContent({ profile, playerId }: { profile: PlayerProfile; playerId: number }) {
  // Same deterministic-by-id color assignment as the leaderboard rows, so a
  // player's identity color matches between the two pages.
  const colorIndex = profile.id % AVATAR_COLORS.length;
  const avatarStyle = {
    '--avatar-bg': AVATAR_COLORS[colorIndex],
    '--avatar-ink': colorIndex >= 3 ? 'var(--tone-black)' : 'var(--white)',
  } as CSSProperties;

  // Single-column DOM order is the mobile order: identity card, stats,
  // rating chart, then match history. Desktop splits into two columns via CSS.
  return (
    <div className={styles.layout}>
      <div className={styles.leftColumn}>
        <div className={styles.identityCard}>
          <div className={styles.avatarWrap}>
            <div className={styles.avatar} style={avatarStyle} aria-hidden="true">
              {profile.name.trim().charAt(0).toUpperCase()}
            </div>
            <span className={styles.rankBadge} aria-label={`Rank ${profile.rank}`}>#{profile.rank}</span>
          </div>
          <h2 className={styles.name}>{profile.name}</h2>
          <span className={styles.playerId}>ID: <span className={styles.ucdttId}>{profile.id}</span></span>
          <dl className={styles.attributes}>
            <div><dt>Style</dt><dd>{profile.style}</dd></div>
            <div><dt>Grip</dt><dd>{profile.grip}</dd></div>
            <div><dt>Registered</dt><dd>{registeredFormatter.format(new Date(profile.created_date))}</dd></div>
          </dl>
        </div>
        <section aria-label="Player statistics">
          <h3 className={styles.sectionHeading}>Stats</h3>
          <div className={styles.statsGrid}>
            <div className={styles.statCard}><span>{profile.total_matches}</span><span>Matches</span></div>
            <div className={styles.statCard}><span>{profile.wins}-{profile.losses}</span><span>Win-Loss</span></div>
            <div className={styles.statCard}><span>{profile.display_rating}</span><span>Current rating</span></div>
            <div className={styles.statCard}><span>{profile.highest_rating}</span><span>Highest rating</span></div>
            <div className={styles.statCard}>
              <span>{profile.win_percentage === null ? '—' : `${profile.win_percentage}%`}</span>
              <span>Win rate</span>
            </div>
          </div>
        </section>
        <section aria-label="Rating history">
          <h3 className={styles.sectionHeading}>Rating over time</h3>
          <RatingChart points={profile.rating_history} />
          {!profile.history_complete && (
            <p className={styles.chartNote}>Showing the most recent 90 days of rating changes.</p>
          )}
        </section>
      </div>
      <div className={styles.rightColumn}>
        <ScopedMatchList
          title="Match history"
          emptyLabel="No matches recorded for this player yet."
          buildPath={(page) => playerMatchesPath(playerId, page)}
          parse={parseMatchPage}
          cardHref={(match) => `#matches/${match.id}`}
        />
      </div>
    </div>
  );
}
