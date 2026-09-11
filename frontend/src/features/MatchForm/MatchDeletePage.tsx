import { useState } from 'react';
import PageLayout from '../../components/PageLayout';
import RequestState from '../../components/RequestState';
import { ApiError } from '../../services/api';
import { authFetch, useAuth } from '../../services/auth';
import useApiResource from '../../services/useApiResource';
import { matchDetailPath, parseMatchDetail } from '../MatchDetail/api';
import styles from './MatchFormPage.module.css';

export default function MatchDeletePage({ matchId }: { matchId: number }) {
  const { username } = useAuth();
  const match = useApiResource(matchDetailPath(matchId), parseMatchDetail);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function deleteMatch() {
    setDeleting(true);
    setError(null);
    try {
      const response = await authFetch(`/api/matches/${matchId}/`, { method: 'DELETE' });
      if (response.status === 204) {
        window.location.hash = '#matches';
        return;
      }
      if (response.status === 401 || response.status === 403) {
        setError('Your officer session expired. Log in again before deleting.');
      } else if (response.status === 404) {
        setError('This match no longer exists.');
      } else {
        setError('The server could not delete this match. Try again.');
      }
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 401
        ? 'Your officer session expired. Log in again before deleting.'
        : 'Could not reach the server. Check the connection and try again.');
    } finally {
      setDeleting(false);
    }
  }

  return (
    <PageLayout title="Delete Match" activePage="matches" backLabel="Back to match detail"
      backHash={`#matches/${matchId}`} showNavigation={false}>
      {!username ? (
        <section className={styles.messagePanel}>
          <h2>Officer login required</h2>
          <p>Log in with an officer account before deleting match records.</p>
          <a href="#login" className={styles.secondaryLink}>Open officer login</a>
        </section>
      ) : match.loading ? (
        <RequestState loading title="Loading match" message="Preparing the confirmation." />
      ) : match.notFound ? (
        <RequestState title="Match not found" message={`No match exists with ID ${matchId}.`} />
      ) : match.error ? (
        <RequestState title="Unable to load match" message={match.error} onRetry={match.retry} />
      ) : match.data ? (
        <section className={styles.deletePanel} aria-labelledby="delete-match-heading">
          <span className={styles.dangerLabel}>Permanent action</span>
          <h2 id="delete-match-heading">Delete {match.data.player1_name} vs. {match.data.player2_name}?</h2>
          <p>
            This removes the match and replays every affected rating from the remaining records.
            This action cannot be undone.
          </p>
          <dl className={styles.deleteSummary}>
            <div><dt>Score</dt><dd>{match.data.score1}–{match.data.score2}</dd></div>
            <div><dt>Date</dt><dd>{new Intl.DateTimeFormat(undefined, { dateStyle: 'long', timeStyle: 'short' }).format(new Date(match.data.date))}</dd></div>
          </dl>
          {error && <p className={styles.formError} role="alert">{error}</p>}
          <div className={styles.formActions}>
            <button type="button" className={styles.deleteButton} disabled={deleting} onClick={deleteMatch}>
              {deleting ? 'Deleting…' : 'Delete match permanently'}
            </button>
          </div>
        </section>
      ) : null}
    </PageLayout>
  );
}
