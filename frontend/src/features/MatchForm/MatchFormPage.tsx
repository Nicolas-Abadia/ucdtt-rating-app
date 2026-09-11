import { useRef, useState, type CSSProperties, type FormEvent } from 'react';
import Icon from '../../components/Icon';
import PageLayout from '../../components/PageLayout';
import RequestState from '../../components/RequestState';
import SearchField from '../../components/SearchField';
import { ApiError } from '../../services/api';
import { authFetch, useAuth } from '../../services/auth';
import useApiResource from '../../services/useApiResource';
import useMagneticDock from '../../services/useMagneticDock';
import { AVATAR_COLORS } from '../../styles/tokens';
import type { MatchSummary } from '../../types/match';
import type { PlayerData } from '../Leaderboard/types';
import { matchDetailPath, parseMatchDetail } from '../MatchDetail/api';
import styles from './MatchFormPage.module.css';

interface MatchFormPageProps { matchId?: number }
interface Draft {
  player1: number | null;
  player2: number | null;
  score1: string;
  score2: string;
  date: string;
}
type FieldName = 'player1' | 'player2' | 'score1' | 'score2' | 'date';
type FieldErrors = Partial<Record<FieldName, string>>;

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function parsePlayers(value: unknown): PlayerData[] {
  if (!Array.isArray(value) || !value.every((player) => record(player)
    && Number.isInteger(player.id) && typeof player.name === 'string'
    && typeof player.display_rating === 'number' && Number.isFinite(player.display_rating)
    && Number.isInteger(player.rank) && Number.isInteger(player.wins) && Number.isInteger(player.losses))) {
    throw new Error('The API did not return the player roster.');
  }
  return value as PlayerData[];
}

function localDateTimeValue(value: string | Date): string {
  const date = value instanceof Date ? value : new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function messageFrom(value: unknown): string | null {
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) {
    const messages = value.map(messageFrom).filter((item): item is string => item !== null);
    return messages.length ? messages.join(' ') : null;
  }
  return null;
}

function apiErrors(value: unknown): { fields: FieldErrors; general: string | null } {
  if (!record(value)) return { fields: {}, general: 'The match could not be saved. Try again.' };
  const fields: FieldErrors = {};
  const general: string[] = [];
  for (const [key, valueForKey] of Object.entries(value)) {
    const message = messageFrom(valueForKey);
    if (!message) continue;
    if (['player1', 'player2', 'score1', 'score2', 'date'].includes(key)) {
      fields[key as FieldName] = message;
    } else {
      general.push(message);
    }
  }
  return { fields, general: general.join(' ') || null };
}

export default function MatchFormPage({ matchId }: MatchFormPageProps) {
  const { username } = useAuth();
  const editing = matchId !== undefined;
  return (
    <PageLayout title={editing ? 'Edit Match' : 'Log Match'} activePage="matches"
      backLabel={editing ? 'Back to match detail' : 'Back to match history'}
      backHash={editing ? `#matches/${matchId}` : '#matches'} showNavigation={false}>
      {!username ? (
        <OfficerRequired />
      ) : editing ? (
        <EditMatchEditor matchId={matchId} />
      ) : (
        <NewMatchEditor />
      )}
    </PageLayout>
  );
}

function OfficerRequired() {
  return (
    <section className={styles.messagePanel}>
      <h2>Officer login required</h2>
      <p>Log in with an officer account before changing match records.</p>
      <a href="#login" className={styles.secondaryLink}>Open officer login</a>
    </section>
  );
}

function NewMatchEditor() {
  const roster = useApiResource('/api/leaderboard/', parsePlayers);
  if (roster.loading) return <RequestState loading title="Loading players" message="Preparing the match form." />;
  if (roster.error) return <RequestState title="Unable to load players" message={roster.error} onRetry={roster.retry} />;
  if (!roster.data || roster.data.length < 2) {
    return <RequestState title="Not enough players" message="At least two players are required to log a match." />;
  }
  return <MatchEditor players={roster.data} />;
}

function EditMatchEditor({ matchId }: { matchId: number }) {
  const roster = useApiResource('/api/leaderboard/', parsePlayers);
  const match = useApiResource(matchDetailPath(matchId), parseMatchDetail);
  if (roster.loading || match.loading) return <RequestState loading title="Loading match" message="Preparing the match editor." />;
  if (match.notFound) return <RequestState title="Match not found" message={`No match exists with ID ${matchId}.`} />;
  if (roster.error) return <RequestState title="Unable to load players" message={roster.error} onRetry={roster.retry} />;
  if (match.error) return <RequestState title="Unable to load match" message={match.error} onRetry={match.retry} />;
  if (!roster.data || !match.data) return null;
  return <MatchEditor key={match.data.id} players={roster.data} match={match.data} />;
}

function MatchEditor({ players, match }: { players: PlayerData[]; match?: MatchSummary }) {
  const [draft, setDraft] = useState<Draft>(() => ({
    player1: match?.player1 ?? null,
    player2: match?.player2 ?? null,
    score1: String(match?.score1 ?? 0),
    score2: String(match?.score2 ?? 0),
    date: match ? localDateTimeValue(match.date) : '',
  }));
  const [picker, setPicker] = useState<'player1' | 'player2' | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const dockRef = useRef<HTMLDivElement>(null);
  useMagneticDock(dockRef);

  const numericScore1 = Number(draft.score1);
  const numericScore2 = Number(draft.score2);
  const matchDate = new Date(draft.date);
  const canSubmit = draft.player1 !== null && draft.player2 !== null
    && draft.player1 !== draft.player2
    && draft.score1 !== '' && draft.score2 !== ''
    && Number.isInteger(numericScore1) && numericScore1 >= 0
    && Number.isInteger(numericScore2) && numericScore2 >= 0
    && numericScore1 !== numericScore2
    && draft.date !== '' && !Number.isNaN(matchDate.getTime());

  function updateScore(field: 'score1' | 'score2', value: string) {
    if (/^\d*$/.test(value)) setDraft((current) => ({ ...current, [field]: value }));
  }

  function validate(): FieldErrors {
    const errors: FieldErrors = {};
    if (draft.player1 === null) errors.player1 = 'Choose Player 1.';
    if (draft.player2 === null) errors.player2 = 'Choose Player 2.';
    if (draft.player1 !== null && draft.player1 === draft.player2) errors.player2 = 'Choose two different players.';
    const score1 = Number(draft.score1);
    const score2 = Number(draft.score2);
    if (draft.score1 === '' || !Number.isInteger(score1) || score1 < 0) errors.score1 = 'Enter a non-negative whole number.';
    if (draft.score2 === '' || !Number.isInteger(score2) || score2 < 0) errors.score2 = 'Enter a non-negative whole number.';
    if (!errors.score1 && !errors.score2 && score1 === score2) errors.score2 = 'One player must win.';
    const date = new Date(draft.date);
    if (!draft.date || Number.isNaN(date.getTime())) errors.date = 'Choose the match date and time.';
    else if (date.getTime() > Date.now()) errors.date = 'Match date cannot be in the future.';
    return errors;
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const clientErrors = validate();
    setFieldErrors(clientErrors);
    setError(null);
    if (Object.keys(clientErrors).length) return;

    setSubmitting(true);
    try {
      const response = await authFetch(match ? `/api/matches/${match.id}/` : '/api/matches/', {
        method: match ? 'PUT' : 'POST',
        body: JSON.stringify({
          player1: draft.player1,
          player2: draft.player2,
          score1: Number(draft.score1),
          score2: Number(draft.score2),
          date: new Date(draft.date).toISOString(),
        }),
      });
      if (response.ok) {
        window.location.hash = match ? `#matches/${match.id}` : '#matches';
        return;
      }
      if (response.status === 401 || response.status === 403) {
        setError('Your officer session expired. Log in again before saving.');
        return;
      }
      let body: unknown = null;
      try { body = await response.json(); } catch { /* non-JSON server error */ }
      const parsed = apiErrors(body);
      setFieldErrors(parsed.fields);
      setError(parsed.general ?? (response.status >= 500
        ? 'The server could not save the match. Try again.'
        : 'Check the highlighted fields and try again.'));
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 401
        ? 'Your officer session expired. Log in again before saving.'
        : 'Could not reach the server. Check the connection and try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <form id="match-form" className={styles.form} onSubmit={submit} noValidate>
        <div className={styles.playerGrid}>
          <PlayerEntry label="Player 1" playerId={draft.player1} players={players}
            score={draft.score1} playerError={fieldErrors.player1} scoreError={fieldErrors.score1}
            onChoose={() => setPicker('player1')}
            onScore={(value) => updateScore('score1', value)} />
          <PlayerEntry label="Player 2" playerId={draft.player2} players={players}
            score={draft.score2} playerError={fieldErrors.player2} scoreError={fieldErrors.score2}
            onChoose={() => setPicker('player2')}
            onScore={(value) => updateScore('score2', value)} />
        </div>

        <section className={styles.dateSection}>
          <label htmlFor="match-date">Date and time</label>
          <div className={styles.dateRow}>
            <input id="match-date" type="datetime-local" value={draft.date}
              aria-invalid={Boolean(fieldErrors.date)}
              onChange={(event) => setDraft((current) => ({ ...current, date: event.target.value }))} />
            <button type="button" className={styles.currentTime}
              onClick={() => setDraft((current) => ({ ...current, date: localDateTimeValue(new Date()) }))}>
              Use current time
            </button>
          </div>
          {fieldErrors.date && <p className={styles.fieldError} role="alert">{fieldErrors.date}</p>}
        </section>

        {error && <p className={styles.formError} role="alert">{error}</p>}
        <div ref={dockRef} className={`${styles.formActionDock} ${canSubmit && !submitting ? styles.attention : ''}`}>
          <button type="submit" className={styles.submit} disabled={!canSubmit || submitting}>
            <span>{submitting ? 'Saving…' : match ? 'Save match' : 'Log this match'}</span>
            <span className={styles.submitArrow} aria-hidden="true"><Icon name="arrow" size={24} /></span>
          </button>
        </div>
      </form>

      {picker && (
        <PlayerPicker players={players}
          selected={draft[picker]}
          excluded={picker === 'player1' ? draft.player2 : draft.player1}
          label={picker === 'player1' ? 'Choose Player 1' : 'Choose Player 2'}
          onClose={() => setPicker(null)}
          onSelect={(playerId) => {
            const field = picker;
            if (!field) return;
            setDraft((current) => ({ ...current, [field]: playerId }));
            setFieldErrors((current) => ({ ...current, [field]: undefined }));
            setPicker(null);
          }} />
      )}
    </>
  );
}

interface PlayerEntryProps {
  label: string;
  playerId: number | null;
  players: PlayerData[];
  score: string;
  playerError?: string;
  scoreError?: string;
  onChoose: () => void;
  onScore: (value: string) => void;
}

function PlayerEntry({ label, playerId, players, score, playerError, scoreError, onChoose, onScore }: PlayerEntryProps) {
  const player = players.find((item) => item.id === playerId) ?? null;
  return (
    <section className={styles.playerEntry}>
      <h2>{label}</h2>
      <button type="button" className={`${styles.playerCard} ${player ? '' : styles.emptyPlayer}`}
        onClick={onChoose} aria-invalid={Boolean(playerError)}
        aria-label={player ? `Change ${label}: ${player.name}` : `Choose ${label}`}>
        {player ? <PlayerIdentity player={player} /> : <>
          <span className={styles.emptyAvatar} aria-hidden="true" />
          <span className={styles.emptyName} aria-hidden="true" />
          <span className={styles.emptyId}>ID:</span>
        </>}
      </button>
      {playerError && <p className={styles.fieldError} role="alert">{playerError}</p>}
      <div className={styles.scoreField}>
        <span className={styles.scoreLabel}>Score</span>
        <div className={styles.stepper}>
          <button type="button" aria-label={`Decrease ${label} score`}
            disabled={Number(score || 0) <= 0} onClick={() => onScore(String(Math.max(0, Number(score || 0) - 1)))}>−</button>
          <input type="text" inputMode="numeric" value={score} aria-label={`${label} score`}
            aria-invalid={Boolean(scoreError)} onChange={(event) => onScore(event.target.value)} />
          <button type="button" aria-label={`Increase ${label} score`}
            onClick={() => onScore(String(Number(score || 0) + 1))}>+</button>
        </div>
      </div>
      {scoreError && <p className={styles.fieldError} role="alert">{scoreError}</p>}
    </section>
  );
}

function PlayerIdentity({ player }: { player: PlayerData }) {
  const colorIndex = player.id % AVATAR_COLORS.length;
  const avatarStyle = {
    '--avatar-bg': AVATAR_COLORS[colorIndex],
    '--avatar-ink': colorIndex >= 3 ? 'var(--tone-black)' : 'var(--white)',
  } as CSSProperties;
  return (
    <>
      <span className={styles.avatar} style={avatarStyle} aria-hidden="true">{player.name.trim().charAt(0).toUpperCase()}</span>
      <span className={styles.playerName}>{player.name}</span>
      <span className={styles.playerMeta}>ID: <strong>{player.id}</strong> · Rating {player.display_rating}</span>
    </>
  );
}

interface PlayerPickerProps {
  players: PlayerData[];
  selected: number | null;
  excluded: number | null;
  label: string;
  onSelect: (playerId: number) => void;
  onClose: () => void;
}

function PlayerPicker({ players, selected, excluded, label, onSelect, onClose }: PlayerPickerProps) {
  const [query, setQuery] = useState('');
  const normalized = query.trim().toLowerCase();
  const visible = players.filter((player) => player.id !== excluded
    && (!normalized || player.name.toLowerCase().includes(normalized) || String(player.id) === normalized.replace(/^#/, '')));
  return (
    <div className={styles.pickerBackdrop} onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className={styles.picker} role="dialog" aria-modal="true" aria-labelledby="player-picker-title">
        <div className={styles.pickerHeader}>
          <h2 id="player-picker-title">{label}</h2>
          <button type="button" className={styles.closePicker} onClick={onClose} aria-label="Close player picker">×</button>
        </div>
        <SearchField value={query} onChange={setQuery} label="Search players by name or ID" placeholder="Search by name or ID" />
        {visible.length ? (
          <ul className={styles.playerOptions}>
            {visible.map((player) => (
              <li key={player.id}>
                <button type="button" className={`${styles.playerOption} ${selected === player.id ? styles.selectedOption : ''}`}
                  onClick={() => onSelect(player.id)}>
                  <PlayerIdentity player={player} />
                </button>
              </li>
            ))}
          </ul>
        ) : <p className={styles.noPlayers} role="status">No matching players.</p>}
      </section>
    </div>
  );
}
