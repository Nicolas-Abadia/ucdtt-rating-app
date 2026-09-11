import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { useAuth } from '../services/auth';
import styles from './LoginForm.module.css';
import controls from './Button.module.css';

interface LoginFormProps {
  // Fired after a successful login (close the dropdown, or leave the page).
  onSuccess?: () => void;
  // Fired after logging out (close the dropdown).
  onLogout?: () => void;
  autoFocus?: boolean;
  // Rendered inside the header's dark pill: lifts the label color for the
  // tone-black surface. The standalone account page uses the default.
  dark?: boolean;
  // Form id so an external control (the navigation dock) can submit it.
  formId?: string;
  // Hide the built-in submit button when the navigation dock owns the action.
  externalSubmit?: boolean;
  onStateChange?: (state: { canSubmit: boolean; busy: boolean }) => void;
}

// The shared officer sign-in surface: the login fields when logged out, and
// the session summary plus logout when logged in. Rendered inside the header
// account panel on desktop and inside the standalone login page on mobile.
export default function LoginForm({ onSuccess, onLogout, autoFocus, dark, formId, externalSubmit, onStateChange }: LoginFormProps) {
  const { username, login, logout } = useAuth();
  const [form, setForm] = useState({ username: '', password: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canSubmit = form.username.trim() !== '' && form.password !== '';

  useEffect(() => {
    onStateChange?.({ canSubmit, busy });
  }, [busy, canSubmit, onStateChange]);

  if (username) {
    return (
      <div className={styles.session}>
        <p className={styles.panelText}>Logged in as <strong>{username}</strong></p>
        <button type="button" className={controls.button}
          onClick={() => { logout(); onLogout?.(); }}>Log out</button>
      </div>
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(form.username.trim(), form.password);
      setForm({ username: '', password: '' });
      onSuccess?.();
    } catch (cause) {
      setError(cause instanceof Error && cause.name !== 'ApiError'
        ? cause.message
        : 'Could not log in. Check the connection and try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <form id={formId} className={`${styles.loginForm} ${dark ? styles.dark : ''}`} onSubmit={submit}>
      <label>
        Username
        <input type="text" autoComplete="username" required autoFocus={autoFocus}
          value={form.username}
          onChange={(event) => setForm({ ...form, username: event.target.value })} />
      </label>
      <label>
        Password
        <input type="password" autoComplete="current-password" required
          value={form.password}
          onChange={(event) => setForm({ ...form, password: event.target.value })} />
      </label>
      {error && <p className={styles.loginError} role="alert">{error}</p>}
      {!externalSubmit && (
        <button type="submit" className={`${controls.button} ${controls.primary}`} disabled={busy}>
          {busy ? 'Logging in...' : 'Officer login'}
        </button>
      )}
    </form>
  );
}
