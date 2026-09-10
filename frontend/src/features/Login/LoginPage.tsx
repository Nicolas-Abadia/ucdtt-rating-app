import Header from '../../components/Header';
import LoginForm from '../../components/LoginForm';
import { useAuth } from '../../services/auth';
import styles from './LoginPage.module.css';

// The standalone officer sign-in screen. Mobile routes here from the header
// account button; desktop keeps the header dropdown but can still reach this
// page directly. After a successful login the officer returns to the
// leaderboard, where the officer controls are now unlocked.
export default function LoginPage() {
  const { username } = useAuth();

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
          <LoginForm autoFocus onSuccess={goHome} />
        </div>
      </main>
    </div>
  );
}
