import { useState } from 'react';
import Header from '../../components/Header';
import LoginForm from '../../components/LoginForm';
import NavigationMenu from '../../components/NavigationMenu';
import { useAuth } from '../../services/auth';
import styles from './LoginPage.module.css';

const LOGIN_FORM_ID = 'officer-login-form';

// The standalone officer sign-in screen. The navigation dock stays visible and
// owns the login action: it breathes with a blue glow once both credentials
// are filled, matching the other confirmation flows. After a successful login
// the officer returns to the leaderboard, where officer controls are unlocked.
export default function LoginPage() {
  const { username } = useAuth();
  const [loginState, setLoginState] = useState({ canSubmit: false, busy: false });

  function goHome() {
    window.location.hash = '#leaderboard';
  }

  return (
    <div className={styles.page}>
      <Header title="Officer Login" backLabel="Back to leaderboard" backHash="#leaderboard" />
      <main className={styles.main}>
        <div className={styles.card}>
          <h2 className={styles.heading}>{username ? 'Officer session' : 'Officer sign in'}</h2>
          <p className={styles.subtitle}>
            {username
              ? 'You have officer access. Log matches and manage players from any page.'
              : 'Log in with your officer credentials to log matches and manage players.'}
          </p>
          <LoginForm autoFocus formId={LOGIN_FORM_ID} externalSubmit={!username}
            onStateChange={setLoginState} onSuccess={goHome} />
        </div>
      </main>
      <NavigationMenu activePage="leaderboard" isOfficer={username !== null}
        primaryAction={username ? undefined : {
          label: 'Officer login',
          activeLabel: 'Logging in…',
          accent: 'blue',
          disabled: !loginState.canSubmit,
          busy: loginState.busy,
          form: LOGIN_FORM_ID,
        }} />
    </div>
  );
}
