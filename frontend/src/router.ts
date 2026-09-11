// Hash routes support refresh and Back/Forward on the static host without
// adding a routing dependency or a deployment rewrite.
export type Route =
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
  | { name: 'officer-new' }
  | { name: 'not-found' };

function parseId(segment: string | undefined): number | null {
  return segment !== undefined && /^[1-9][0-9]*$/.test(segment) ? Number(segment) : null;
}

export function parseRoute(hash: string): Route {
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
  if (head === 'officers' && sub === 'new' && segments.length === 2) return { name: 'officer-new' };
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
