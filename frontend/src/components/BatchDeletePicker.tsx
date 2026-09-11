import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { createPortal } from 'react-dom';
import RequestState from './RequestState';
import SearchField from './SearchField';
import { ApiError, getJson } from '../services/api';
import { authFetch } from '../services/auth';
import useApiResource from '../services/useApiResource';
import { AVATAR_COLORS } from '../styles/tokens';
import { parsePlayers } from '../features/Leaderboard/api';
import { parseBatchResult, parseMatchCardPage, type BatchResult } from './batchDeleteApi';
import type { MatchSummary } from '../types/match';
import styles from './BatchDeletePicker.module.css';

export type BatchKind = 'players' | 'matches';

interface BatchDeletePickerProps {
  kind: BatchKind;
  onClose: () => void;
}

const optionDate = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' });

// Officer multi-delete in the match form's picker pattern: search, toggle
// rows, then a two-step red confirmation. Closing after a successful delete
// reloads, so the page behind shows the data without the deleted rows.
// Portaled to document.body: the navigation dock uses transform, and a fixed
// overlay inside a transformed ancestor would pin itself to the dock.
export default function BatchDeletePicker({ kind, onClose }: BatchDeletePickerProps) {
  const noun = kind === 'players' ? 'players' : 'matches';
  const singular = kind === 'players' ? 'player' : 'match';
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<ReadonlySet<number>>(new Set());
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BatchResult | null>(null);
  const [closing, setClosing] = useState(false);

  function handleClose() {
    // After a successful delete, closing reloads so the page shows fresh data.
    if (result) {
      window.location.reload();
      return;
    }
    // Play the exit animation first; onClose runs on animationend.
    setClosing(true);
  }

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Escape' || deleting) return;
      handleClose();
    }
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  });

  function toggle(id: number) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setConfirming(false);
  }

  async function confirm() {
    if (selected.size === 0 || deleting) return;
    if (!confirming) {
      setConfirming(true);
      setError(null);
      return;
    }
    setDeleting(true);
    setError(null);
    try {
      const response = await authFetch(`/api/${kind}/batch-delete/`, {
        method: 'POST',
        body: JSON.stringify({ ids: [...selected] }),
      });
      if (response.ok) {
        setResult(parseBatchResult(await response.json()));
        return;
      }
      if (response.status === 401 || response.status === 403) {
        setError('Your officer session expired. Log in again before deleting.');
      } else if (response.status === 400) {
        setError('The selection could not be deleted. Pick the rows again and retry.');
      } else {
        setError('The server could not delete the selection. Try again.');
      }
      setConfirming(false);
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 401
        ? 'Your officer session expired. Log in again before deleting.'
        : 'Could not reach the server. Check the connection and try again.');
      setConfirming(false);
    } finally {
      setDeleting(false);
    }
  }

  return createPortal(
    <div className={`${styles.backdrop} ${closing ? styles.closing : ''}`}
      onAnimationEnd={() => { if (closing) onClose(); }}
      onPointerDown={(event) => {
        if (event.target === event.currentTarget && !deleting) handleClose();
      }}>
      <div className={styles.panel} role="dialog" aria-modal="true" aria-labelledby="batch-delete-heading">
        <div className={styles.header}>
          <h2 id="batch-delete-heading">Delete {noun}</h2>
          <button type="button" className={styles.closeButton} onClick={handleClose} disabled={deleting}
            aria-label="Close">×</button>
        </div>
        {result ? (
          <div className={styles.summary}>
            <p className={styles.summaryText}>
              <strong>{result.deleted}</strong> {result.deleted === 1 ? singular : noun} deleted.
            </p>
            {result.skipped.length > 0 && (
              <div className={styles.skipped}>
                <h3>Skipped</h3>
                <ul className={styles.skippedList}>
                  {result.skipped.map((item) => (
                    <li key={item.id}><strong>{item.name ?? `#${item.id}`}</strong> — {item.reason}</li>
                  ))}
                </ul>
              </div>
            )}
            <button type="button" className={styles.doneButton} onClick={() => window.location.reload()}>Done</button>
          </div>
        ) : (
          <>
            <SearchField value={query} onChange={setQuery}
              label={kind === 'players' ? 'Search players by name or ID' : 'Search matches by player name or ID'}
              placeholder={kind === 'players' ? 'Search by name or ID' : 'Search by player name or match ID'} />
            {kind === 'players' ? (
              <PlayerOptions query={query} selected={selected} onToggle={toggle} />
            ) : (
              <MatchOptions query={query} selected={selected} onToggle={toggle} />
            )}
            {error && <p className={styles.error} role="alert">{error}</p>}
            <button type="button" className={`${styles.confirm} ${confirming ? styles.confirming : ''}`}
              disabled={selected.size === 0 || deleting} onClick={confirm}>
              {deleting ? 'Deleting…'
                : confirming ? `Confirm delete ${selected.size} ${selected.size === 1 ? singular : noun}`
                : selected.size === 0 ? `Delete ${noun}`
                : `Delete ${selected.size} selected`}
            </button>
          </>
        )}
      </div>
    </div>,
    document.body,
  );
}

interface OptionsProps {
  query: string;
  selected: ReadonlySet<number>;
  onToggle: (id: number) => void;
}

function PlayerOptions({ query, selected, onToggle }: OptionsProps) {
  const roster = useApiResource('/api/leaderboard/', parsePlayers);
  if (roster.loading) return <RequestState loading title="Loading players" />;
  if (roster.error) return <RequestState title="Unable to load players" message={roster.error} onRetry={roster.retry} />;
  const q = query.trim().toLowerCase();
  const visible = (roster.data ?? []).filter((player) =>
    !q || player.name.toLowerCase().includes(q) || String(player.id) === q);
  if (visible.length === 0) return <p className={styles.empty} role="status">No matching players.</p>;
  return (
    <ul className={styles.options}>
      {visible.map((player) => {
        const colorIndex = player.id % AVATAR_COLORS.length;
        const avatarStyle = {
          '--avatar-bg': AVATAR_COLORS[colorIndex],
          '--avatar-ink': colorIndex >= 3 ? 'var(--tone-black)' : 'var(--white)',
        } as CSSProperties;
        const isSelected = selected.has(player.id);
        return (
          <li key={player.id}>
            <button type="button" className={`${styles.option} ${isSelected ? styles.selected : ''}`}
              aria-pressed={isSelected} onClick={() => onToggle(player.id)}>
              <span className={styles.optionAvatar} style={avatarStyle} aria-hidden="true">
                {player.name.trim().charAt(0).toUpperCase()}
              </span>
              <span className={styles.optionBody}>
                <span className={styles.optionName} title={player.name}>{player.name}</span>
                <span className={styles.optionMeta}>ID: {player.id} · Rating {player.display_rating}</span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function MatchOptions({ query, selected, onToggle }: OptionsProps) {
  const trimmed = query.trim();
  const [page, setPage] = useState(1);
  const [prevTrimmed, setPrevTrimmed] = useState(trimmed);
  const [items, setItems] = useState<MatchSummary[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [settled, setSettled] = useState<{ key: string } | null>(null);
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const requestRef = useRef(0);

  // Reset to the first page when the search text changes. Adjusting state in
  // render is the sanctioned alternative to a setState-in-effect reset.
  if (prevTrimmed !== trimmed) {
    setPrevTrimmed(trimmed);
    setPage(1);
  }

  // Loading and error are derived per request, so the fetch effect only ever
  // sets state in async callbacks, never synchronously in its body.
  const requestKey = `${trimmed}|${page}|${reloadKey}`;
  const loading = settled?.key !== requestKey;
  const error = failure?.key === requestKey ? failure.message : null;

  useEffect(() => {
    const requestId = ++requestRef.current;
    const controller = new AbortController();
    getJson(`/api/matches/?include=card&q=${encodeURIComponent(trimmed)}&page=${page}`, controller.signal)
      .then((value) => parseMatchCardPage(value))
      .then((result) => {
        if (requestId !== requestRef.current) return;
        setItems((current) => (page === 1 ? result.results : [...current, ...result.results]));
        setNext(result.next);
        setSettled({ key: requestKey });
      })
      .catch((caught) => {
        if (controller.signal.aborted || requestId !== requestRef.current) return;
        setFailure({
          key: requestKey,
          message: caught instanceof ApiError && caught.status === 404
            ? 'No matches found.'
            : 'Could not load matches. Check the connection and try again.',
        });
        setSettled({ key: requestKey });
      });
    return () => controller.abort();
  }, [trimmed, page, reloadKey, requestKey]);

  if (error) {
    return <RequestState title="Unable to load matches" message={error}
      onRetry={() => setReloadKey((current) => current + 1)} />;
  }
  return (
    <>
      {items.length === 0 && !loading ? (
        <p className={styles.empty} role="status">No matches found.</p>
      ) : (
        <ul className={styles.options}>
          {items.map((match) => {
            const isSelected = selected.has(match.id);
            const label = `${match.player1_name} vs ${match.player2_name}`;
            return (
              <li key={match.id}>
                <button type="button" className={`${styles.option} ${isSelected ? styles.selected : ''}`}
                  aria-pressed={isSelected} onClick={() => onToggle(match.id)}>
                  <span className={styles.optionBody}>
                    <span className={styles.optionName} title={label}>{label}</span>
                    <span className={styles.optionMeta}>
                      ID: {match.id} · {match.score1}-{match.score2} ·{' '}
                      <time dateTime={match.date}>{optionDate.format(new Date(match.date))}</time>
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {loading && <p className={styles.empty} role="status">Loading…</p>}
      {next && !loading && (
        <button type="button" className={styles.loadMore} onClick={() => setPage((current) => current + 1)}>
          Load more
        </button>
      )}
    </>
  );
}
