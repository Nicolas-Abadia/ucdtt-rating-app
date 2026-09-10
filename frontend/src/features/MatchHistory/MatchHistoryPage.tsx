import { useRef, useState } from 'react';
import PageLayout from '../../components/PageLayout';
import RequestState from '../../components/RequestState';
import SearchField from '../../components/SearchField';
import MatchList from './components/MatchList';
import useMatches from './useMatches';
import styles from './MatchHistoryPage.module.css';
import controls from '../../components/Button.module.css';

export default function MatchHistoryPage() {
  const [filters, setFilters] = useState({ query: '', date: '', page: 1 });
  const { data, loading, error, retry } = useMatches(filters.query.trim(), filters.page, filters.date);
  const hasFilters = Boolean(filters.query.trim() || filters.date);
  const resultsRef = useRef<HTMLDivElement>(null);

  function search(query: string) {
    setFilters((current) => ({ ...current, query, page: 1 }));
  }

  function goToPage(page: number) {
    setFilters((current) => ({ ...current, page }));
    resultsRef.current?.scrollIntoView({ block: 'start', behavior: 'instant' });
    resultsRef.current?.focus({ preventScroll: true });
  }

  return (
    <PageLayout title="Match History" activePage="matches">
      <section className={styles.panel} aria-label="Recorded matches">
        <div className={styles.searchGroup}>
          <div className={styles.filterRow}>
            <SearchField value={filters.query} onChange={search}
              label="Search by player name or match ID"
              placeholder="Search by player name or match ID" />
            <div className={styles.dateFilter}>
              <input type="date" value={filters.date} aria-label="Filter matches by date"
                onChange={(event) => setFilters((current) => ({ ...current, date: event.target.value, page: 1 }))} />
            </div>
          </div>
          {hasFilters && <div className={styles.filterActions}>
            <button type="button" className={controls.button}
              onClick={() => setFilters({ query: '', date: '', page: 1 })}>Clear filters</button>
          </div>}
        </div>
        <div ref={resultsRef} tabIndex={-1} className={styles.results} aria-label="Match results" aria-busy={loading}>
          {loading ? (
            <RequestState loading title="Loading matches" message="The server may take a moment to respond." />
          ) : error ? (
            <>
              <RequestState title="Unable to load matches" message={error} onRetry={retry} />
              {filters.page > 1 && <button type="button" className={controls.button} onClick={() => goToPage(1)}>Return to first page</button>}
            </>
          ) : data && data.results.length === 0 ? (
            <div className={styles.empty} role="status">
              <h2>{hasFilters ? 'No matches found' : 'No matches recorded'}</h2>
            </div>
          ) : data ? (
            <>
              <p className={styles.resultCount} role="status">{data.count} {data.count === 1 ? 'match' : 'matches'} · Page {filters.page}</p>
              <MatchList matches={data.results} />
              <nav className={styles.pagination} aria-label="Match history pages">
                <button type="button" className={controls.button} disabled={!data.previous} onClick={() => goToPage(filters.page - 1)}>Previous</button>
                <span>Page {filters.page}</span>
                <button type="button" className={controls.button} disabled={!data.next} onClick={() => goToPage(filters.page + 1)}>Next</button>
              </nav>
            </>
          ) : null}
        </div>
      </section>
    </PageLayout>
  );
}
