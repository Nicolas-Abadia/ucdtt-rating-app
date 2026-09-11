import { useRef, useState, type FormEvent } from 'react';
import Icon from '../../components/Icon';
import OfficerRequired from '../../components/OfficerRequired';
import PageLayout from '../../components/PageLayout';
import { ApiError, messageFrom, record } from '../../services/api';
import { authFetch, useAuth } from '../../services/auth';
import useMagneticDock from '../../services/useMagneticDock';
import dock from '../../components/FormDock.module.css';
// The shared officer-form styles: fields, notes, errors, success panel.
import styles from '../OfficerForm/OfficerFormPage.module.css';

type FieldName = 'username' | 'old_password' | 'new_password1' | 'new_password2';
type FieldErrors = Partial<Record<FieldName, string>>;

// Server field names land back on the matching inputs; anything else is a
// page-level message.
const KEYMAP: Record<string, FieldName | undefined> = {
  username: 'username',
  old_password: 'old_password',
  new_password1: 'new_password1',
  new_password2: 'new_password2',
};

function apiErrors(value: unknown): { fields: FieldErrors; general: string | null } {
  if (!record(value)) return { fields: {}, general: 'The account could not be updated. Try again.' };
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

function parseUpdate(value: unknown): { username: string; changed: string[] } {
  if (!record(value) || typeof value.username !== 'string' || !Array.isArray(value.changed)
    || !value.changed.every((item) => typeof item === 'string')) {
    throw new Error('The API did not return the account update.');
  }
  return { username: value.username, changed: value.changed as string[] };
}

// The signed-in officer's own account: rename and password change in one
// submit, mirroring the HTML account page (which the API reuses).
export default function AccountPage() {
  const { username } = useAuth();
  return (
    <PageLayout title="Account" activePage="leaderboard"
      backLabel="Back to officer session" backHash="#login" showNavigation={false}>
      {!username ? (
        <OfficerRequired message="Log in with an officer account before changing account settings." />
      ) : (
        <AccountEditor currentUsername={username} />
      )}
    </PageLayout>
  );
}

function AccountEditor({ currentUsername }: { currentUsername: string }) {
  const { renameUsername } = useAuth();
  const [form, setForm] = useState({
    username: currentUsername,
    old_password: '',
    new_password1: '',
    new_password2: '',
  });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [saved, setSaved] = useState<string[] | null>(null);
  const [shaking, setShaking] = useState(false);
  const dockRef = useRef<HTMLDivElement>(null);
  useMagneticDock(dockRef);

  const changingPassword = form.old_password !== '' || form.new_password1 !== '' || form.new_password2 !== '';
  const usernameChanged = form.username.trim() !== '' && form.username.trim() !== currentUsername;
  const passwordReady = !changingPassword
    || (form.old_password !== '' && form.new_password1.length >= 8 && form.new_password1 === form.new_password2);
  const canSubmit = form.username.trim() !== '' && (usernameChanged || changingPassword) && passwordReady;

  function update(field: FieldName, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setFieldErrors((current) => ({ ...current, [field]: undefined }));
  }

  function validate(): FieldErrors {
    const errors: FieldErrors = {};
    if (!form.username.trim()) errors.username = 'Choose a username.';
    if (changingPassword) {
      if (!form.old_password) errors.old_password = 'Enter your current password.';
      if (!form.new_password1) errors.new_password1 = 'Choose a new password.';
      else if (form.new_password1.length < 8) errors.new_password1 = 'Use at least 8 characters.';
      if (form.new_password2 !== form.new_password1) errors.new_password2 = 'The two passwords do not match.';
    }
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
      const response = await authFetch('/api/account/', {
        method: 'POST',
        body: JSON.stringify({
          username: form.username.trim(),
          old_password: form.old_password,
          new_password1: form.new_password1,
          new_password2: form.new_password2,
        }),
      });
      if (response.ok) {
        const updated = parseUpdate(await response.json());
        if (updated.changed.includes('username')) renameUsername(updated.username);
        setSaved(updated.changed);
        return;
      }
      if (response.status === 401 || response.status === 403) {
        setError('Your officer session expired. Log in again before changing the account.');
        return;
      }
      let body: unknown = null;
      try { body = await response.json(); } catch { /* non-JSON server error */ }
      const parsed = apiErrors(body);
      setFieldErrors(parsed.fields);
      if (response.status === 400) setShaking(true);
      setError(parsed.general ?? (response.status >= 500
        ? 'The server could not update the account. Try again.'
        : null));
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 401
        ? 'Your officer session expired. Log in again before changing the account.'
        : 'Could not reach the server. Check the connection and try again.');
    } finally {
      setSubmitting(false);
    }
  }

  if (saved) {
    return (
      <section className={styles.successPanel}>
        <h2>{saved.length ? 'Account updated' : 'No changes submitted'}</h2>
        <p>{saved.length
          ? `Updated the ${saved.join(' and ')}.`
          : 'Nothing was different, so nothing was saved.'}</p>
        <div className={styles.successActions}>
          <a href="#login" className={styles.secondaryButton}>Back to officer session</a>
        </div>
      </section>
    );
  }

  return (
    <form id="account-form" className={styles.form} onSubmit={submit} noValidate>
      <section className={styles.field}>
        <label className={styles.fieldLabel} htmlFor="account-username">Username</label>
        <input id="account-username" type="text" autoComplete="username" value={form.username}
          aria-invalid={Boolean(fieldErrors.username)}
          onChange={(event) => update('username', event.target.value)} />
        <p className={styles.note}>Used to sign in. Letters, digits and @ . + - _ only.</p>
        {fieldErrors.username && <p className={styles.fieldError} role="alert">{fieldErrors.username}</p>}
      </section>

      <section className={styles.field}>
        <label className={styles.fieldLabel} htmlFor="account-current">Current password</label>
        <input id="account-current" type="password" autoComplete="current-password" value={form.old_password}
          aria-invalid={Boolean(fieldErrors.old_password)}
          onChange={(event) => update('old_password', event.target.value)} />
        <p className={styles.note}>Required only to change the password.</p>
        {fieldErrors.old_password && <p className={styles.fieldError} role="alert">{fieldErrors.old_password}</p>}
      </section>

      <section className={styles.field}>
        <label className={styles.fieldLabel} htmlFor="account-new">New password</label>
        <input id="account-new" type="password" autoComplete="new-password" value={form.new_password1}
          aria-invalid={Boolean(fieldErrors.new_password1)}
          onChange={(event) => update('new_password1', event.target.value)} />
        {fieldErrors.new_password1 && <p className={styles.fieldError} role="alert">{fieldErrors.new_password1}</p>}
      </section>

      <section className={styles.field}>
        <label className={styles.fieldLabel} htmlFor="account-confirm">Confirm new password</label>
        <input id="account-confirm" type="password" autoComplete="new-password" value={form.new_password2}
          aria-invalid={Boolean(fieldErrors.new_password2)}
          onChange={(event) => update('new_password2', event.target.value)} />
        {fieldErrors.new_password2 && <p className={styles.fieldError} role="alert">{fieldErrors.new_password2}</p>}
      </section>

      {error && <p className={styles.formError} role="alert">{error}</p>}
      <div ref={dockRef} onAnimationEnd={() => setShaking(false)}
        className={`${dock.formActionDock} ${dock.blue} ${canSubmit && !submitting ? dock.attention : ''} ${shaking ? dock.shake : ''}`}>
        <button type="submit" className={dock.submit} disabled={!canSubmit || submitting}>
          <span>{submitting ? 'Saving…' : 'Save changes'}</span>
          <span className={dock.submitArrow} aria-hidden="true"><Icon name="arrow" size={24} /></span>
        </button>
      </div>
    </form>
  );
}
