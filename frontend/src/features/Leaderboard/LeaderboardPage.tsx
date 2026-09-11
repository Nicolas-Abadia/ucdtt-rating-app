import PageLayout from '../../components/PageLayout';
import RequestState from '../../components/RequestState';
import useApiResource from '../../services/useApiResource';
import Leaderboard from './components/Leaderboard';
import type { PlayerData } from './types';

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function parsePlayers(value: unknown): PlayerData[] {
  if (!Array.isArray(value) || !value.every((player) => record(player)
    && Number.isInteger(player.id) && typeof player.name === 'string'
    && typeof player.display_rating === 'number' && Number.isFinite(player.display_rating)
    && Number.isInteger(player.rank) && Number.isInteger(player.wins) && Number.isInteger(player.losses))) {
    throw new Error('The API did not return the leaderboard.');
  }
  return value as PlayerData[];
}

// The leaderboard uses the same generic fetch hook as the other pages, so a
// dead backend offers the same Try again recovery everywhere.
export default function LeaderboardPage() {
  const roster = useApiResource('/api/leaderboard/', parsePlayers);

  return (
    <PageLayout title="Leaderboard" activePage="leaderboard">
      {roster.loading ? (
        <RequestState loading title="Loading leaderboard" message="The server may take a moment to respond." />
      ) : roster.error ? (
        <RequestState title="Unable to load players" message={roster.error} onRetry={roster.retry} />
      ) : roster.data ? (
        <Leaderboard players={roster.data} />
      ) : null}
    </PageLayout>
  );
}
