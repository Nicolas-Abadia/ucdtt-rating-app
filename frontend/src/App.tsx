import { useEffect, useRef, useSyncExternalStore } from 'react';
import LeaderboardPage from './features/Leaderboard/LeaderboardPage';
import MatchHistoryPage from './features/MatchHistory/MatchHistoryPage';
import PlayerProfilePage from './features/PlayerProfile/PlayerProfilePage';
import PlayerFormPage from './features/PlayerForm/PlayerFormPage';
import MatchDetailPage from './features/MatchDetail/MatchDetailPage';
import NotFoundPage from './components/NotFoundPage';
import LoginPage from './features/Login/LoginPage';
import MatchFormPage from './features/MatchForm/MatchFormPage';
import ImportPage from './features/Import/ImportPage';
import OfficerFormPage from './features/OfficerForm/OfficerFormPage';
import AccountPage from './features/Account/AccountPage';
import { parseRoute, type Route } from './router';

// Hash routes support refresh and Back/Forward on the static host without
// adding a routing dependency or a deployment rewrite.
function subscribe(callback: () => void) {
  window.addEventListener('hashchange', callback);
  return () => window.removeEventListener('hashchange', callback);
}
// The snapshot stays a primitive string so useSyncExternalStore never sees a
// "changed" value when nothing actually changed; routes are parsed from it
// in the render body instead of inside the snapshot getter.
function currentHash() {
  return window.location.hash;
}

const titles: Record<Route['name'], string> = {
  leaderboard: 'Leaderboard',
  matches: 'Match History',
  player: 'Player Profile',
  'player-new': 'Add Player',
  'player-edit': 'Edit Player',
  match: 'Match Detail',
  'match-new': 'Log Match',
  'match-edit': 'Edit Match',
  import: 'Import CSV',
  login: 'Officer Login',
  'officer-new': 'Add Officer',
  account: 'Account',
  'not-found': 'Not Found',
};

export default function App() {
  const hash = useSyncExternalStore(subscribe, currentHash, () => '');
  const route = parseRoute(hash);
  const previous = useRef(route.name);
  useEffect(() => {
    document.title = `${titles[route.name]} | Table Tennis Rating App`;
    if (previous.current !== route.name) {
      window.scrollTo({ top: 0, behavior: 'instant' });
      document.querySelector<HTMLElement>('header h1')?.focus({ preventScroll: true });
      previous.current = route.name;
    }
  }, [route.name]);

  switch (route.name) {
    case 'matches': return <MatchHistoryPage />;
    case 'player': return <PlayerProfilePage playerId={route.id} />;
    case 'player-new': return <PlayerFormPage />;
    case 'player-edit': return <PlayerFormPage playerId={route.id} />;
    case 'match': return <MatchDetailPage matchId={route.id} />;
    case 'match-new': return <MatchFormPage />;
    case 'match-edit': return <MatchFormPage matchId={route.id} />;
    case 'import': return <ImportPage key={route.kind} kind={route.kind} />;
    case 'login': return <LoginPage />;
    case 'officer-new': return <OfficerFormPage />;
    case 'account': return <AccountPage />;
    case 'not-found': return <NotFoundPage />;
    default: return <LeaderboardPage />;
  }
}
