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

type Route =
  | { name: 'leaderboard' }
  | { name: 'matches' }
  | { name: 'player'; id: number }
  | { name: 'player-new' }
  | { name: 'player-edit'; id: number }
  | { name: 'match'; id: number }
  | { name: 'match-new' }
  | { name: 'match-edit'; id: number }
  | { name: 'import'; kind: 'players' | 'matches' }
  | { name: 'login' }
  | { name: 'not-found' };

function parseId(segment: string | undefined): number | null {
  return segment !== undefined && /^[1-9][0-9]*$/.test(segment) ? Number(segment) : null;
}

function parseRoute(hash: string): Route {
  const segments = hash.replace(/^#/, '').split('/').filter(Boolean);
  const [head, sub, action] = segments;
  if (segments.length === 0 || (head === 'leaderboard' && segments.length === 1)) return { name: 'leaderboard' };
  if (head === 'matches') {
    if (segments.length === 1) return { name: 'matches' };
    if (sub === 'new' && segments.length === 2) return { name: 'match-new' };
    const id = parseId(sub);
    if (id === null) return { name: 'not-found' };
    if (segments.length === 2) return { name: 'match', id };
    if (segments.length === 3 && action === 'edit') return { name: 'match-edit', id };
    return { name: 'not-found' };
  }
  if (head === 'login' && segments.length === 1) return { name: 'login' };
  if (head === 'import') {
    if (segments.length === 1) return { name: 'import', kind: 'players' };
    if (segments.length === 2 && sub === 'matches') return { name: 'import', kind: 'matches' };
    return { name: 'not-found' };
  }
  if (head === 'players') {
    if (sub === 'new' && segments.length === 2) return { name: 'player-new' };
    const id = parseId(sub);
    if (id === null) return { name: 'not-found' };
    if (segments.length === 2) return { name: 'player', id };
    if (segments.length === 3 && action === 'edit') return { name: 'player-edit', id };
    return { name: 'not-found' };
  }
  return { name: 'not-found' };
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
    case 'not-found': return <NotFoundPage />;
    default: return <LeaderboardPage />;
  }
}
