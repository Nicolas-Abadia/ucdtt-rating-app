import { useRef, useState } from 'react';
import type { ReactNode } from 'react';
import type { MatchPage, MatchSummary } from '../types/match';
import { groupMatchesByDay } from '../features/MatchHistory/groupMatchesByDay';
import useApiResource from '../services/useApiResource';
import MatchCard from './MatchCard';
import RequestState from './RequestState';
import styles from '../features/MatchHistory/MatchHistoryPage.module.css';
import controls from './Button.module.css';

interface ScopedMatchListProps<T extends MatchPage> {
  title: string;
  emptyLabel: string;
  buildPath: (page: number) => string;
  parse: (value: unknown) => T;
  variant?: 'gold' | 'blue';
  cardHref?: (match: MatchSummary) => string;
  renderSummary?: (data: T) => ReactNode;
}

// Shared paginated, day-grouped match list for player history and
// match head-to-head. Independent loading/error/empty/retry/pagination,
// reusing the existing grouping helper and MatchCard component.
export default function ScopedMatchList<T extends MatchPage>({
  title, emptyLabel, buildPath, parse, variant, cardHref, renderSummary,
}: ScopedMatchListProps<T>) {
  const [page, setPage] = useState(1);
  const path = buildPath(page);
  const { data, loading, error, retry } = useApiResource(path, parse);
  const resultsRef = useRef<HTMLDivElement>(null);

  function goToPage(next: number) {
    setPage(next);
    resultsRef.current?.scrollIntoView({ block: 'start', behavior: 'instant' });
  }

  const groups = data ? groupMatchesByDay(data.results) : [];

  return (
    <section aria-label={title}>
      <h2>{title}</h2>
      <div ref={resultsRef} aria-busy={loading}>
        {loading ? (
          <RequestState loading title="Loading matches" />
        ) : error ? (
          <RequestState title="Unable to load matches" message={error} onRetry={retry} />
        ) : data && data.results.length === 0 ? (
          <p className={styles.empty}>{emptyLabel}</p>
        ) : data ? (
          <>
            {renderSummary && <p className={styles.resultCount}>{renderSummary(data)}</p>}
            <div className={styles.dayGroups}>
              {groups.map((group) => (
                <div key={group.dayKey} className={styles.dayGroup}>
                  <h3 className={styles.dateHeading}>{group.label}</h3>
                  <ul className={styles.matchList}>
                    {group.matches.map((match) => (
                      <li key={match.id}>
                        <MatchCard match={match} variant={variant} href={cardHref?.(match)} />
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            {(data.next || data.previous) && (
              <nav className={styles.pagination} aria-label={`${title} pages`}>
                <button type="button" className={controls.button} disabled={!data.previous} onClick={() => goToPage(page - 1)}>Previous</button>
                <span>Page {page}</span>
                <button type="button" className={controls.button} disabled={!data.next} onClick={() => goToPage(page + 1)}>Next</button>
              </nav>
            )}
          </>
        ) : null}
      </div>
    </section>
  );
}
