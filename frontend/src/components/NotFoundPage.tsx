import PageLayout from './PageLayout';
import RequestState from './RequestState';

// Route-level not-found: the hash did not match any known page or its ID
// segment was not a plain positive integer. Data-level 404s (a well-formed
// ID that does not exist) are handled inside PlayerProfilePage/MatchDetailPage.
export default function NotFoundPage() {
  return (
    <PageLayout title="Not Found" activePage="leaderboard" backLabel="Back to leaderboard" backHash="#leaderboard">
      <RequestState title="Page not found" message="That address does not match anything in the app." />
    </PageLayout>
  );
}
