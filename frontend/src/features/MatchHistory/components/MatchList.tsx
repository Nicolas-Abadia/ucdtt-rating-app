import { useId } from 'react';
import MatchCard from '../../../components/MatchCard';
import { groupMatchesByDay } from '../groupMatchesByDay';
import type { MatchSummary } from '../../../types/match';
import styles from '../MatchHistoryPage.module.css';

export default function MatchList({ matches }: { matches: MatchSummary[] }) {
  const headingPrefix = useId();
  const groups = groupMatchesByDay(matches);
  return (
    <div className={styles.dayGroups}>
      {groups.map((group) => (
        <section key={group.dayKey} className={styles.dayGroup} aria-labelledby={`${headingPrefix}-${group.dayKey}`}>
          <h2 id={`${headingPrefix}-${group.dayKey}`} className={styles.dateHeading}>
            <time dateTime={group.dayKey}>{group.label}</time>
          </h2>
          <ul className={styles.matchList}>
            {group.matches.map((match) => <li key={match.id}><MatchCard match={match} href={`#matches/${match.id}`} /></li>)}
          </ul>
        </section>
      ))}
    </div>
  );
}
