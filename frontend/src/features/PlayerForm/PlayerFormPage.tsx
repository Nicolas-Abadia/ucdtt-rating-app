import { useRef, useState, type CSSProperties, type FormEvent } from 'react';
import Icon from '../../components/Icon';
import PageLayout from '../../components/PageLayout';
import RequestState from '../../components/RequestState';
import { ApiError } from '../../services/api';
import { authFetch, useAuth } from '../../services/auth';
import useApiResource from '../../services/useApiResource';
import useMagneticDock from '../../services/useMagneticDock';
import { AVATAR_COLORS } from '../../styles/tokens';
import dock from '../../components/FormDock.module.css';
import styles from './PlayerFormPage.module.css';

interface PlayerFormPageProps { playerId?: number }

interface PlayerDraft {
  name: string;
  initialRating: string;
  style: string;
  grip: string;
}
type FieldName = 'name' | 'initialRating' | 'style' | 'grip';
type FieldErrors = Partial<Record<FieldName, string>>;

interface PlayerRecord {
  id: number;
  name: string;
  initial_rating: number;
  style: string;
  grip: string;
  created_date: string;
}

// Keep in sync with Player.Style / Player.Grip on the backend.
const STYLE_OPTIONS = [
  { value: '', label: 'Not set' },
  { value: 'offensive', label: 'Offensive' },
  { value: 'all-round', label: 'All-round' },
  { value: 'defensive', label: 'Defensive' },
];
const GRIP_OPTIONS = [
  { value: '', label: 'Not set' },
  { value: 'shakehand', label: 'Shakehand' },
  { value: 'penhold', label: 'Penhold' },
];
// The selectors show only real choices; both fields are optional, so tapping
// the active segment clears it back to unset.
const STYLE_SEGMENTS = STYLE_OPTIONS.filter((option) => option.value !== '');
const GRIP_SEGMENTS = GRIP_OPTIONS.filter((option) => option.value !== '');

const registeredFormatter = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' });

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function parsePlayer(value: unknown): PlayerRecord {
  if (!record(value) || !Number.isInteger(value.id) || typeof value.name !== 'string'
    || !Number.isInteger(value.initial_rating)
    || typeof value.style !== 'string' || typeof value.grip !== 'string'
    || typeof value.created_date !== 'string') {
    throw new Error('The API did not return the player.');
  }
  return value as unknown as PlayerRecord;
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
  if (!record(value)) return { fields: {}, general: 'The player could not be saved. Try again.' };
  const fields: FieldErrors = {};
  const general: string[] = [];
  const keyMap: Record<string, FieldName> = {
    name: 'name', initial_rating: 'initialRating', style: 'style', grip: 'grip',
  };
  for (const [key, valueForKey] of Object.entries(value)) {
    const message = messageFrom(valueForKey);
    if (!message) continue;
    const field = keyMap[key];
    if (field) fields[field] = message;
    else general.push(message);
  }
  return { fields, general: general.join(' ') || null };
}

// New players have no id yet, so the preview colors a typed name the same way
// the officer avatar hashes a username. Once created, the card switches to the
// id-based color used everywhere else.
function nameColorIndex(name: string): number {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) | 0;
  }
  return Math.abs(hash) % AVATAR_COLORS.length;
}

export default function PlayerFormPage({ playerId }: PlayerFormPageProps) {
  const { username } = useAuth();
  const editing = playerId !== undefined;
  return (
    <PageLayout title={editing ? 'Edit Player' : 'Add Player'} activePage="leaderboard"
      backLabel={editing ? 'Back to player profile' : 'Back to leaderboard'}
      backHash={editing ? `#players/${playerId}` : '#leaderboard'} showNavigation={false}>
      {!username ? (
        <OfficerRequired />
      ) : editing ? (
        <EditPlayerForm playerId={playerId} />
      ) : (
        <PlayerEditor />
      )}
    </PageLayout>
  );
}

function OfficerRequired() {
  return (
    <section className={styles.messagePanel}>
      <h2>Officer login required</h2>
      <p>Log in with an officer account before changing player records.</p>
      <a href="#login" className={styles.secondaryLink}>Open officer login</a>
    </section>
  );
}

function EditPlayerForm({ playerId }: { playerId: number }) {
  const player = useApiResource(`/api/players/${playerId}/`, parsePlayer);
  if (player.loading) return <RequestState loading title="Loading player" message="Preparing the player editor." />;
  if (player.notFound) return <RequestState title="Player not found" message={`No player exists with ID ${playerId}.`} />;
  if (player.error) return <RequestState title="Unable to load player" message={player.error} onRetry={player.retry} />;
  if (!player.data) return null;
  return <PlayerEditor key={player.data.id} player={player.data} />;
}

// Live preview of the card the roster will show, mirroring the player profile
// identity card. Empty name renders the same skeleton template as the match
// form's empty player slot.
function PreviewCard({ draft, player }: { draft: PlayerDraft; player?: PlayerRecord }) {
  const name = draft.name.trim();
  const empty = name === '';
  const colorIndex = player ? player.id % AVATAR_COLORS.length : nameColorIndex(name.toLowerCase());
  const avatarStyle = {
    '--avatar-bg': AVATAR_COLORS[colorIndex],
    '--avatar-ink': colorIndex >= 3 ? 'var(--tone-black)' : 'var(--white)',
  } as CSSProperties;
  const styleLabel = STYLE_OPTIONS.find((option) => option.value === draft.style)?.label;
  const gripLabel = GRIP_OPTIONS.find((option) => option.value === draft.grip)?.label;
  return (
    <div className={`${styles.previewCard} ${empty ? styles.previewEmpty : ''}`}>
      {empty ? (
        <>
          <span className={styles.previewAvatarSkeleton} aria-hidden="true" />
          <span className={styles.previewNameSkeleton} aria-hidden="true" />
        </>
      ) : (
        <>
          <div className={styles.previewAvatar} style={avatarStyle} aria-hidden="true">
            {name.charAt(0).toUpperCase()}
          </div>
          <span className={styles.previewName}>{name}</span>
        </>
      )}
      <span className={styles.previewId}>ID: <span className={styles.previewUcdttId}>{player ? player.id : '—'}</span></span>
      <dl className={styles.previewAttributes}>
        <div><dt>Style</dt><dd>{draft.style === '' ? '—' : styleLabel}</dd></div>
        <div><dt>Grip</dt><dd>{draft.grip === '' ? '—' : gripLabel}</dd></div>
        <div><dt>Registered</dt><dd>{player ? registeredFormatter.format(new Date(player.created_date)) : 'Today'}</dd></div>
        <div><dt>Init. rating</dt><dd>{draft.initialRating || '—'}</dd></div>
      </dl>
    </div>
  );
}

interface SegmentedFieldProps {
  label: string;
  options: Array<{ value: string; label: string }>;
  value: string;
  error?: string;
  onChange: (value: string) => void;
}

function SegmentedField({ label, options, value, error, onChange }: SegmentedFieldProps) {
  return (
    <section className={styles.field}>
      <span className={styles.fieldLabel}>{label}</span>
      <div className={styles.segmented} role="group" aria-label={label}>
        {options.map((option) => {
          const active = value === option.value;
          return (
            <button key={option.value} type="button"
              className={`${styles.segment} ${active ? styles.segmentActive : ''}`}
              aria-pressed={active}
              onClick={() => onChange(active ? '' : option.value)}>
              {option.label}
            </button>
          );
        })}
      </div>
      {error && <p className={styles.fieldError} role="alert">{error}</p>}
    </section>
  );
}

function PlayerEditor({ player }: { player?: PlayerRecord }) {
  const [draft, setDraft] = useState<PlayerDraft>(() => ({
    name: player?.name ?? '',
    initialRating: String(player?.initial_rating ?? 1200),
    style: player?.style ?? '',
    grip: player?.grip ?? '',
  }));
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [shaking, setShaking] = useState(false);
  const dockRef = useRef<HTMLDivElement>(null);
  useMagneticDock(dockRef);

  const rating = Number(draft.initialRating);
  const currentRating = draft.initialRating === '' ? 100 : rating;
  const canSubmit = draft.name.trim() !== ''
    && draft.initialRating !== '' && Number.isInteger(rating) && rating >= 100
    && STYLE_OPTIONS.some((option) => option.value === draft.style)
    && GRIP_OPTIONS.some((option) => option.value === draft.grip);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const clientErrors: FieldErrors = {};
    if (draft.name.trim() === '') clientErrors.name = 'Enter the player name.';
    if (draft.initialRating === '' || !Number.isInteger(rating) || rating < 100) {
      clientErrors.initialRating = 'Enter a whole number of at least 100.';
    }
    setFieldErrors(clientErrors);
    setError(null);
    if (Object.keys(clientErrors).length) {
      setShaking(true);
      return;
    }

    setSubmitting(true);
    try {
      const response = await authFetch(player ? `/api/players/${player.id}/` : '/api/players/', {
        method: player ? 'PUT' : 'POST',
        body: JSON.stringify({
          name: draft.name.trim(),
          initial_rating: rating,
          style: draft.style,
          grip: draft.grip,
        }),
      });
      if (response.ok) {
        window.location.hash = player ? `#players/${player.id}` : '#leaderboard';
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
      // Field-level validation errors are marked on the fields themselves;
      // the dock shakes red instead of showing a generic "check fields" card.
      if (response.status === 400) setShaking(true);
      setError(parsed.general ?? (response.status >= 500
        ? 'The server could not save the player. Try again.'
        : null));
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 401
        ? 'Your officer session expired. Log in again before saving.'
        : 'Could not reach the server. Check the connection and try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form id="player-form" className={styles.form} onSubmit={submit} noValidate>
      <section className={styles.field} aria-label="Player preview">
        <span className={styles.fieldLabel}>Preview</span>
        <PreviewCard draft={draft} player={player} />
      </section>

      <section className={styles.field}>
        <label htmlFor="player-name">Name</label>
        <input id="player-name" type="text" autoComplete="off" maxLength={200}
          value={draft.name} aria-invalid={Boolean(fieldErrors.name)}
          onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))} />
        {fieldErrors.name && <p className={styles.fieldError} role="alert">{fieldErrors.name}</p>}
      </section>

      <section className={styles.field}>
        <label htmlFor="player-rating">Initial rating</label>
        <div className={styles.ratingControl}>
          <button type="button" className={styles.ratingStep}
            aria-label="Decrease initial rating by 10"
            disabled={currentRating <= 100}
            onClick={() => setDraft((current) => ({ ...current, initialRating: String(Math.max(100, currentRating - 10)) }))}>−</button>
          <input id="player-rating" type="text" inputMode="numeric"
            className={styles.ratingInput}
            value={draft.initialRating} aria-invalid={Boolean(fieldErrors.initialRating)}
            aria-describedby="player-rating-note"
            onChange={(event) => {
              if (/^\d*$/.test(event.target.value)) {
                setDraft((current) => ({ ...current, initialRating: event.target.value }));
              }
            }} />
          <button type="button" className={styles.ratingStep}
            aria-label="Increase initial rating by 10"
            onClick={() => setDraft((current) => ({ ...current, initialRating: String(currentRating + 10) }))}>+</button>
        </div>
        <p id="player-rating-note" className={styles.note}>
          {player
            ? 'Changing the initial rating replays every rating computed from it.'
            : 'The rating this player starts from. The roster default is 1200.'}
        </p>
        {fieldErrors.initialRating && <p className={styles.fieldError} role="alert">{fieldErrors.initialRating}</p>}
      </section>

      <SegmentedField label="Style" options={STYLE_SEGMENTS} value={draft.style} error={fieldErrors.style}
        onChange={(value) => setDraft((current) => ({ ...current, style: value }))} />
      <SegmentedField label="Grip" options={GRIP_SEGMENTS} value={draft.grip} error={fieldErrors.grip}
        onChange={(value) => setDraft((current) => ({ ...current, grip: value }))} />

      {error && <p className={styles.formError} role="alert">{error}</p>}
      <div ref={dockRef} onAnimationEnd={() => setShaking(false)}
        className={`${dock.formActionDock} ${dock.blue} ${canSubmit && !submitting ? dock.attention : ''} ${shaking ? dock.shake : ''}`}>
        <button type="submit" className={dock.submit} disabled={!canSubmit || submitting}>
          <span>{submitting ? 'Saving…' : player ? 'Save player' : 'Add player'}</span>
          <span className={dock.submitArrow} aria-hidden="true"><Icon name="arrow" size={24} /></span>
        </button>
      </div>
    </form>
  );
}
