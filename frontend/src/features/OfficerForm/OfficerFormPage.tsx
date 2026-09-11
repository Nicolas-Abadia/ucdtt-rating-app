import { useRef, useState, type FormEvent } from 'react';
import Icon from '../../components/Icon';
import OfficerRequired from '../../components/OfficerRequired';
import PageLayout from '../../components/PageLayout';
import { ApiError, messageFrom, record } from '../../services/api';
import { authFetch, useAuth } from '../../services/auth';
import useMagneticDock from '../../services/useMagneticDock';
import dock from '../../components/FormDock.module.css';
import styles from './OfficerFormPage.module.css';

type FieldName = 'username' | 'password1' | 'password2';
type FieldErrors = Partial<Record<FieldName, string>>;

// Server field names land back on the matching inputs; anything else is a
// page-level message.
const KEYMAP: Record<string, FieldName | undefined> = {
  username: 'username',
  password1: 'password1',
  password2: 'password2',
};

function apiErrors(value: unknown): { fields: FieldErrors; general: string | null } {
  if (!record(value)) return { fields: {}, general: 'The officer account could not be created. Try again.' };
  const fields: FieldErrors = {};
  const general: string[] = [];
  for (const [key, valueForKey] of Object.entries(value)) {
    const message = messageFrom(valueForKey);
    if (!message) continue;
    const field = KEYMAP[key];
    if (field) fields[field] = message;
    else general.push(message);
  }
  return { fields, general: general.join(' ') || null };
}

// Officer-only account creation, linked from the session panel. Mirrors the
// server-rendered signup: the API reuses its form, so username rules and the
// configured password validators apply identically here.
export default function OfficerFormPage() {
  const { username } = useAuth();
  return (
    <PageLayout title="Add Officer" activePage="leaderboard"
      backLabel="Back to officer session" backHash="#login" showNavigation={false}>
      {!username ? (
        <OfficerRequired message="Log in with an officer account before creating officer accounts." />
      ) : (
        <OfficerEditor />
      )}
    </PageLayout>
  );
}

function OfficerEditor() {
  const [form, setForm] = useState({ username: '', password1: '', password2: '' });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState<string | null>(null);
  const [shaking, setShaking] = useState(false);
  const dockRef = useRef<HTMLDivElement>(null);
  useMagneticDock(dockRef);

  const canSubmit = form.username.trim() !== '' && form.password1 !== ''
    && form.password2 !== '' && form.password1 === form.password2;

  function update(field: FieldName, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setFieldErrors((current) => ({ ...current, [field]: undefined }));
  }

  function validate(): FieldErrors {
    const errors: FieldErrors = {};
    if (!form.username.trim()) errors.username = 'Choose a username.';
    if (!form.password1) errors.password1 = 'Choose a password.';
    else if (form.password1.length < 8) errors.password1 = 'Use at least 8 characters.';
    if (form.password2 !== form.password1) errors.password2 = 'The two passwords do not match.';
    return errors;
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const clientErrors = validate();
    setFieldErrors(clientErrors);
    setError(null);
    if (Object.keys(clientErrors).length) {
      setShaking(true);
      return;
    }

    setSubmitting(true);
    try {
      const response = await authFetch('/api/officers/', {
        method: 'POST',
        body: JSON.stringify({
          username: form.username.trim(),
          password1: form.password1,
          password2: form.password2,
        }),
      });
      if (response.ok) {
        setCreated(form.username.trim());
        return;
      }
      if (response.status === 401 || response.status === 403) {
        setError('Your officer session expired. Log in again before creating an account.');
        return;
      }
      let body: unknown = null;
      try { body = await response.json(); } catch { /* non-JSON server error */ }
      const parsed = apiErrors(body);
      setFieldErrors(parsed.fields);
      if (response.status === 400) setShaking(true);
      setError(parsed.general ?? (response.status >= 500
        ? 'The server could not create the account. Try again.'
        : null));
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 401
        ? 'Your officer session expired. Log in again before creating an account.'
        : 'Could not reach the server. Check the connection and try again.');
    } finally {
      setSubmitting(false);
    }
  }

  function reset() {
    setCreated(null);
    setForm({ username: '', password1: '', password2: '' });
    setFieldErrors({});
    setError(null);
  }

  if (created) {
    return (
      <section className={styles.successPanel}>
        <h2>Officer account created</h2>
        <p><strong>{created}</strong> can sign in now with the password just set.</p>
        <div className={styles.successActions}>
          <button type="button" className={styles.secondaryButton} onClick={reset}>Add another officer</button>
          <a href="#login" className={styles.secondaryButton}>Back to officer session</a>
        </div>
      </section>
    );
  }

  return (
    <form id="officer-form" className={styles.form} onSubmit={submit} noValidate>
      <section className={styles.field}>
        <label className={styles.fieldLabel} htmlFor="officer-username">Username</label>
        <input id="officer-username" type="text" autoComplete="off" value={form.username}
          aria-invalid={Boolean(fieldErrors.username)}
          onChange={(event) => update('username', event.target.value)} />
        <p className={styles.note}>Used to sign in. Letters, digits and @ . + - _ only.</p>
        {fieldErrors.username && <p className={styles.fieldError} role="alert">{fieldErrors.username}</p>}
      </section>

      <section className={styles.field}>
        <label className={styles.fieldLabel} htmlFor="officer-password">Password</label>
        <input id="officer-password" type="password" autoComplete="new-password" value={form.password1}
          aria-invalid={Boolean(fieldErrors.password1)}
          onChange={(event) => update('password1', event.target.value)} />
        <p className={styles.note}>At least 8 characters, not too similar to the username, not a common password.</p>
        {fieldErrors.password1 && <p className={styles.fieldError} role="alert">{fieldErrors.password1}</p>}
      </section>

      <section className={styles.field}>
        <label className={styles.fieldLabel} htmlFor="officer-confirm">Confirm password</label>
        <input id="officer-confirm" type="password" autoComplete="new-password" value={form.password2}
          aria-invalid={Boolean(fieldErrors.password2)}
          onChange={(event) => update('password2', event.target.value)} />
        {fieldErrors.password2 && <p className={styles.fieldError} role="alert">{fieldErrors.password2}</p>}
      </section>

      {error && <p className={styles.formError} role="alert">{error}</p>}
      <div ref={dockRef} onAnimationEnd={() => setShaking(false)}
        className={`${dock.formActionDock} ${dock.blue} ${canSubmit && !submitting ? dock.attention : ''} ${shaking ? dock.shake : ''}`}>
        <button type="submit" className={dock.submit} disabled={!canSubmit || submitting}>
          <span>{submitting ? 'Creating…' : 'Create officer account'}</span>
          <span className={dock.submitArrow} aria-hidden="true"><Icon name="arrow" size={24} /></span>
        </button>
      </div>
    </form>
  );
}
