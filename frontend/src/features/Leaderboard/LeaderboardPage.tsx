import PageLayout from '../../components/PageLayout';
import RequestState from '../../components/RequestState';
import useApiResource from '../../services/useApiResource';
import { parsePlayers } from './api';
import Leaderboard from './components/Leaderboard';

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
