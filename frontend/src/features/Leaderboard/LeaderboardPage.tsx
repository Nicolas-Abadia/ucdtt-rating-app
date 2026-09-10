import { useEffect, useState } from 'react';
import PageLayout from '../../components/PageLayout';
import RequestState from '../../components/RequestState';
import { apiUrl } from '../../services/api';
import Leaderboard from './components/Leaderboard';
import type { PlayerData } from './types';

export default function LeaderboardPage() {
  const [players, setPlayers] = useState<PlayerData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(apiUrl('/api/leaderboard/'), { signal: controller.signal })
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
    <PageLayout title="Leaderboard" activePage="leaderboard">
      {isLoading ? (
        <RequestState loading title="Loading leaderboard" message="The server may take a moment to respond." />
      ) : error ? (
        <RequestState title="Unable to load players" message={error} />
      ) : (
        <Leaderboard players={players} />
      )}
    </PageLayout>
  );
}
