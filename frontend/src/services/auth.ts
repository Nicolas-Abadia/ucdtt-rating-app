import { useSyncExternalStore } from 'react';
import { apiUrl, ApiError } from './api';

// Officer session state. The JWT pair is stored in localStorage so a session
// survives reloads; the access token is refreshed through
// /api/token/refresh/ when it is within 10 seconds of expiring. There is no
// server-side logout endpoint wired, so logging out discards the pair
// client-side (the blacklisted refresh rotation bounds the residue).

const STORAGE_KEY = 'ttapp.auth';
const EXPIRY_BUFFER_MS = 10_000;

interface Session {
  access: string;
  refresh: string;
  username: string;
}

function load(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<Session>;
    if (typeof parsed.access === 'string' && typeof parsed.refresh === 'string'
      && typeof parsed.username === 'string') {
      return parsed as Session;
    }
  } catch { /* corrupted storage: start logged out */ }
  return null;
}

let session: Session | null = load();
const listeners = new Set<() => void>();

function save(next: Session | null) {
  session = next;
  if (next) localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  else localStorage.removeItem(STORAGE_KEY);
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

// JWT payload is base64url JSON; exp is seconds since the epoch. An
// undecodable token is treated as expired so it is refreshed rather than sent.
function expiryMs(token: string): number {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))) as { exp?: unknown };
    return typeof payload.exp === 'number' ? payload.exp * 1000 : 0;
  } catch {
    return 0;
  }
}

export async function login(username: string, password: string): Promise<void> {
  const response = await fetch(apiUrl('/api/token/'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (response.status === 401) throw new Error('Incorrect username or password.');
  if (!response.ok) throw new ApiError(response.status);
  const data = await response.json() as { access?: unknown; refresh?: unknown };
  if (typeof data.access !== 'string' || typeof data.refresh !== 'string') {
    throw new Error('The API did not return a session. The backend must include the JWT update.');
  }
  save({ access: data.access, refresh: data.refresh, username });
}

export async function logout() {
  const current = session;
  // Clear first so the UI reacts immediately, then invalidate the refresh
  // token server-side. Best effort: a network failure still leaves the pair
  // discarded locally.
  save(null);
  if (!current) return;
  try {
    await fetch(apiUrl('/api/token/blacklist/'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ refresh: current.refresh }),
    });
  } catch { /* the pair is already discarded client-side */ }
}

// Single-flight: concurrent requests share one refresh round-trip instead of
// racing to rotate the same refresh token twice (the second would be
// blacklisted and log the officer out).
let refreshing: Promise<string | null> | null = null;

function refreshAccessToken(): Promise<string | null> {
  const current = session;
  if (!current) return Promise.resolve(null);
  refreshing ??= (async () => {
    try {
      const response = await fetch(apiUrl('/api/token/refresh/'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ refresh: current.refresh }),
      });
      if (!response.ok) {
        save(null);
        return null;
      }
      const data = await response.json() as { access?: unknown; refresh?: unknown };
      if (typeof data.access !== 'string') {
        save(null);
        return null;
      }
      // ROTATE_REFRESH_TOKENS returns a fresh refresh token too; keep the
      // previous one if the response ever omits it.
      save({
        access: data.access,
        refresh: typeof data.refresh === 'string' ? data.refresh : current.refresh,
        username: current.username,
      });
      return data.access;
    } catch {
      return null;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

async function accessToken(): Promise<string | null> {
  if (!session) return null;
  if (expiryMs(session.access) > Date.now() + EXPIRY_BUFFER_MS) return session.access;
  return refreshAccessToken();
}

// Authenticated request helper for the write endpoints. Attaches the current
// access token and retries once after a refresh if the server still answered
// 401 (the token can expire between the local check and the request).
export async function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = await accessToken();
  if (!token) throw new ApiError(401);
  const send = (bearer: string) => fetch(apiUrl(path), {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...init.headers,
      Authorization: `Bearer ${bearer}`,
    },
  });
  let response = await send(token);
  if (response.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) response = await send(refreshed);
  }
  return response;
}

export function useAuth() {
  const current = useSyncExternalStore(subscribe, () => session, () => null);
  return { username: current?.username ?? null, login, logout };
}
