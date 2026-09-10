import { useEffect, useRef, useSyncExternalStore } from 'react';
import LeaderboardPage from './features/Leaderboard/LeaderboardPage';
import MatchHistoryPage from './features/MatchHistory/MatchHistoryPage';
import PlayerProfilePage from './features/PlayerProfile/PlayerProfilePage';
import MatchDetailPage from './features/MatchDetail/MatchDetailPage';
import NotFoundPage from './components/NotFoundPage';

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
  | { name: 'match'; id: number }
  | { name: 'not-found' };

function parseId(segment: string | undefined): number | null {
  return segment !== undefined && /^[1-9][0-9]*$/.test(segment) ? Number(segment) : null;
}

function parseRoute(hash: string): Route {
  const path = hash.replace(/^#/, '');
  const [head, sub] = path.split('/');
  if (!head || head === 'leaderboard') return { name: 'leaderboard' };
  if (head === 'matches') {
    if (sub === undefined) return { name: 'matches' };
    const id = parseId(sub);
    return id === null ? { name: 'not-found' } : { name: 'match', id };
  }
  if (head === 'players') {
    const id = parseId(sub);
    return id === null ? { name: 'not-found' } : { name: 'player', id };
  }
  return { name: 'not-found' };
}

const titles: Record<Route['name'], string> = {
  leaderboard: 'Leaderboard',
  matches: 'Match History',
  player: 'Player Profile',
  match: 'Match Detail',
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
    case 'match': return <MatchDetailPage matchId={route.id} />;
    case 'not-found': return <NotFoundPage />;
    default: return <LeaderboardPage />;
  }
}
