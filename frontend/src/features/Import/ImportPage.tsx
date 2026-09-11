import { useRef, useState, type CSSProperties } from 'react';
import Icon from '../../components/Icon';
import OfficerRequired from '../../components/OfficerRequired';
import PageLayout from '../../components/PageLayout';
import { ApiError, messageFrom, record } from '../../services/api';
import { authFetch, useAuth } from '../../services/auth';
import useMagneticDock from '../../services/useMagneticDock';
import { AVATAR_COLORS, nameColorIndex } from '../../styles/tokens';
import dock from '../../components/FormDock.module.css';
import { parsePreview, type MatchPreviewRow, type PlayerPreviewRow, type PreviewPayload, type SkippedRow } from './api';
import styles from './ImportPage.module.css';

export type ImportKind = 'players' | 'matches';

interface ImportPageProps { kind: ImportKind }

// Instruction text matches the HTML importer (players/views.py).
const KIND_CONFIG: Record<ImportKind, {
  title: string;
  noun: string;
  columns: string[];
  notes: string;
  example: string;
  backHash: string;
  backLabel: string;
}> = {
  players: {
    title: 'Player CSV import',
    noun: 'players',
    columns: ['name'],
    notes: 'rating is optional and defaults to 1200. A player who is already on the roster is skipped, never overwritten, and the comparison ignores capitalisation.',
    example: 'name,rating\nAlice Chen,1350\nBen Ortiz,',
    backHash: '#leaderboard',
    backLabel: 'Back to leaderboard',
  },
  matches: {
    title: 'Match CSV import',
    noun: 'matches',
    columns: ['player1', 'player2', 'score1', 'score2', 'date'],
    notes: 'player1 and player2 must already be on the roster; a name that is not there is skipped rather than created. A date without a UTC offset is read in your own timezone. The file does not need to be in date order.',
    example: 'player1,player2,score1,score2,date\nAlice Chen,Ben Ortiz,11,7,2026-08-20 19:30',
    backHash: '#matches',
    backLabel: 'Back to match history',
  },
};

const previewDate = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' });

export default function ImportPage({ kind }: ImportPageProps) {
  const { username } = useAuth();
  const config = KIND_CONFIG[kind];
  return (
    <PageLayout title={config.title} activePage={kind === 'matches' ? 'matches' : 'leaderboard'}
      backLabel={config.backLabel} backHash={config.backHash} showNavigation={false}>
      {!username ? (
        <OfficerRequired message="Log in with an officer account before importing records." />
      ) : (
        <ImportEditor kind={kind} />
      )}
    </PageLayout>
  );
}

// Two steps mirroring the HTML importer: the chosen file uploads once to
// preview, and the same file goes back with ?confirm=1 only when the officer
// confirms from the dock. Nothing writes on preview.
function ImportEditor({ kind }: ImportPageProps) {
  const config = KIND_CONFIG[kind];
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewPayload | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [shaking, setShaking] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dockRef = useRef<HTMLDivElement>(null);
  useMagneticDock(dockRef);

  const canImport = preview !== null && preview.rows.length > 0 && !previewing && !submitting;
  const dockReady = preview === null ? !previewing && !submitting : canImport;

  async function upload(confirm: boolean, selected: File) {
    const body = new FormData();
    body.append('csv_file', selected);
    return authFetch(`/api/${kind}/import/${confirm ? '?confirm=1' : ''}`, { method: 'POST', body });
  }

  // Returns true when the response was a failure that has been reported.
  async function handleFailure(response: Response): Promise<boolean> {
    if (response.ok) return false;
    if (response.status === 401 || response.status === 403) {
      setError('Your officer session expired. Log in again before importing.');
      return true;
    }
    if (response.status === 400) {
      // File-level validation: mark the file card and shake the dock, the
      // same signal as the other write forms.
      setShaking(true);
      let message: string | null = null;
      try {
        const body: unknown = await response.json();
        if (record(body)) {
          message = messageFrom(body.csv_file) ?? messageFrom(body.detail) ?? messageFrom(body.non_field_errors);
        }
      } catch { /* non-JSON validation error */ }
      setFieldError(message ?? 'The file could not be imported. Check the format and try again.');
      return true;
    }
    setError('The server could not import the file. Try again.');
    return true;
  }

  function handleException(caught: unknown) {
    setError(caught instanceof ApiError && caught.status === 401
      ? 'Your officer session expired. Log in again before importing.'
      : 'Could not reach the server. Check the connection and try again.');
  }

  async function previewFile(selected: File) {
    setPreviewing(true);
    setError(null);
    setFieldError(null);
    setPreview(null);
    try {
      const response = await upload(false, selected);
      if (await handleFailure(response)) return;
      setPreview(parsePreview(await response.json(), kind));
    } catch (caught) {
      handleException(caught);
    } finally {
      setPreviewing(false);
    }
  }

  async function confirmImport() {
    if (!file || !canImport) return;
    setSubmitting(true);
    setError(null);
    try {
      const response = await upload(true, file);
      if (await handleFailure(response)) return;
      // No completion page: the updated leaderboard or match history is the
      // confirmation.
      window.location.hash = config.backHash;
    } catch (caught) {
      handleException(caught);
    } finally {
      setSubmitting(false);
    }
  }

  function onFileChange(selected: File | null) {
    setFile(selected);
    setPreview(null);
    setFieldError(null);
    setError(null);
    if (selected) void previewFile(selected);
  }

  return (
    <div className={styles.form}>
      <section className={styles.instructions} aria-label="File format">
        <p className={styles.required}>
          Required columns:{' '}
          {config.columns.map((column, index) => (
            <span key={column}>{index > 0 && ', '}<span className={styles.columnName}>{column}</span></span>
          ))}
        </p>
        <p className={styles.note}>{config.notes}</p>
        <div className={styles.example}>
          <span className={styles.exampleLabel}>Example file:</span>
          <pre className={styles.exampleCode}>{config.example}</pre>
        </div>
      </section>

      <section className={styles.field}>
        <span className={styles.fieldLabel} id="csv-file-label">Import CSV</span>
        <input ref={fileInputRef} type="file" accept=".csv,text/csv" className={styles.fileInput}
          aria-labelledby="csv-file-label"
          onChange={(event) => onFileChange(event.target.files?.[0] ?? null)} />
        <button type="button" className={`${styles.fileCard} ${file ? styles.fileCardPicked : ''}`}
          onClick={() => fileInputRef.current?.click()} aria-invalid={Boolean(fieldError)}>
          <Icon name="upload" size={file ? 20 : 30} />
          <span className={styles.fileName}>{file ? 'Import a different file' : 'Choose a CSV file'}</span>
          <span className={styles.fileHint} title={file ? file.name : undefined}>{file ? file.name : `Columns: ${config.columns.join(', ')}`}</span>
        </button>
        {fieldError && <p className={styles.fieldError} role="alert">{fieldError}</p>}
      </section>

      {previewing && <p className={styles.note} role="status">Reading {file?.name}…</p>}
      {preview && (
        <section className={styles.previewSection} aria-labelledby="import-preview-heading">
          <h2 id="import-preview-heading" className={styles.previewHeading}>
            Preview of {preview.filename}: {preview.rows.length} row{preview.rows.length === 1 ? '' : 's'} would be imported:
          </h2>
          {preview.rows.length > 0 && (
            <ul className={styles.cardList}>
              {preview.rows.map((row, index) => (
                <li key={index}>
                  {kind === 'players'
                    ? <PlayerPreviewCard row={row as PlayerPreviewRow} />
                    : <MatchPreviewCard row={row as MatchPreviewRow} />}
                </li>
              ))}
            </ul>
          )}
          {preview.skipped.length > 0 && <SkippedList rows={preview.skipped} />}
        </section>
      )}

      {error && <p className={styles.formError} role="alert">{error}</p>}
      <div ref={dockRef} onAnimationEnd={() => setShaking(false)}
        className={`${dock.formActionDock} ${dock.purple} ${dockReady ? dock.attention : ''} ${shaking ? dock.shake : ''}`}>
        <button type="button" className={dock.submit} disabled={!dockReady}
          onClick={preview ? confirmImport : () => fileInputRef.current?.click()}>
          <span>{submitting ? 'Importing…'
            : preview ? `Import these ${preview.rows.length} row${preview.rows.length === 1 ? '' : 's'}?`
            : previewing ? 'Reading…'
            : 'Upload CSV'}</span>
          <span className={dock.submitArrow} aria-hidden="true"><Icon name="arrow" size={24} /></span>
        </button>
      </div>
    </div>
  );
}

// Player rows preview as leaderboard cards: identity color, initial, name,
// seeded rating, and the zeroed record every new player starts with.
function PlayerPreviewCard({ row }: { row: PlayerPreviewRow }) {
  const colorIndex = nameColorIndex(row.name.toLowerCase());
  const avatarStyle = {
    '--avatar-bg': AVATAR_COLORS[colorIndex],
    '--avatar-ink': colorIndex >= 3 ? 'var(--tone-black)' : 'var(--white)',
  } as CSSProperties;
  return (
    <article className={styles.playerCard} aria-label={`New player: ${row.name}, rating ${row.rating}`}>
      <div className={styles.playerAvatar} style={avatarStyle} aria-hidden="true">
        {row.name.trim().charAt(0).toUpperCase()}
      </div>
      <div className={styles.playerBody}>
        <span className={styles.playerName} title={row.name}>{row.name}</span>
        <div className={styles.stats}>
          <span className={styles.stat}><Icon name="rating" size={16} />{row.rating}</span>
          <span className={styles.stat}><Icon name="win" size={16} />0 won</span>
          <span className={styles.stat}><Icon name="loss" size={16} />0 lost</span>
        </div>
      </div>
    </article>
  );
}

// Match rows preview as match-history cards without a rating delta: the
// match has not been recorded yet, so there is no change to show.
function MatchPreviewCard({ row }: { row: MatchPreviewRow }) {
  const firstWon = row.score1 > row.score2;
  return (
    <article className={styles.matchCard} aria-label={`${row.player1} versus ${row.player2}`}>
      <span className={`${styles.score} ${firstWon ? styles.winner : ''}`}
        aria-label={`${row.player1}: ${row.score1}${firstWon ? ', winner' : ''}`}>{row.score1}</span>
      <div className={styles.matchBody}>
        <div className={styles.matchMeta}>
          <time dateTime={row.date} title={new Date(row.date).toLocaleString()}>
            {previewDate.format(new Date(row.date))}
          </time>
        </div>
        <div className={styles.matchPlayers}>
          <div className={styles.matchPlayer}><span className={styles.matchName} title={row.player1}>{row.player1}</span></div>
          <div className={styles.matchPlayer}><span className={styles.matchName} title={row.player2}>{row.player2}</span></div>
        </div>
      </div>
      <span className={`${styles.score} ${!firstWon ? styles.winner : ''}`}
        aria-label={`${row.player2}: ${row.score2}${!firstWon ? ', winner' : ''}`}>{row.score2}</span>
    </article>
  );
}

function SkippedList({ rows }: { rows: SkippedRow[] }) {
  return (
    <div className={styles.skipped}>
      <h3>Skipped rows</h3>
      <ul className={styles.rowList}>
        {rows.map((row) => (
          <li key={row.line}><span className={styles.lineNumber}>Line {row.line}</span> {row.reason}</li>
        ))}
      </ul>
    </div>
  );
}
