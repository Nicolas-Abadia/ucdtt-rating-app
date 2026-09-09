import { useEffect, useState } from 'react';
import Header from '../../components/Header';
import NavigationMenu from '../../components/NavigationMenu';
import Leaderboard from './components/Leaderboard';
import styles from './LeaderboardPage.module.css';
import type { PlayerData } from './types';

export default function LeaderboardPage() {
  const [players, setPlayers] = useState<PlayerData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
    fetch(`${baseUrl}/api/leaderboard/`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed with status ${res.status}`);
        return res.json();
      })
      .then((data: PlayerData[]) => {
        if (controller.signal.aborted) return;
        if (!Array.isArray(data)) throw new Error('Invalid leaderboard response');
        setPlayers(data);
        setIsLoading(false);
      })
      .catch(() => {
        if (controller.signal.aborted) return;
        setError('Could not load the leaderboard. Please try again later.');
        setIsLoading(false);
      });
    return () => controller.abort();
  }, []);

  return (
    <div id="leaderboard" className={styles.page}>
      <Header title="Leaderboard" />
      <main className={styles.main}>
        {isLoading ? (
          <div className={styles.loadingContainer} role="status">
            <div className={styles.spinner} aria-hidden="true" />
            <h2>Loading leaderboard</h2>
            <p>The server may take a moment to respond.</p>
          </div>
        ) : error ? (
          <div className={styles.errorContainer} role="alert"><h2>Unable to load players</h2><p>{error}</p></div>
        ) : (
          <Leaderboard players={players} />
        )}
      </main>
      <NavigationMenu />
    </div>
  );
}
