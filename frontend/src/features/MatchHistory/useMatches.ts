import { useEffect, useState } from 'react';
import type { MatchPage } from '../../types/match';
import { fetchMatches } from './api';

interface Result {
  key: string;
  data: MatchPage | null;
  error: string | null;
}

export default function useMatches(query: string, page: number, date = '') {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<Result | null>(null);
  const key = JSON.stringify([query, page, date, attempt]);

  useEffect(() => {
    const controller = new AbortController();
    let disposed = false;
    let timedOut = false;
    let timeout: number | undefined;
    const debounce = window.setTimeout(async () => {
      timeout = window.setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, 90000);
      try {
        const data = await fetchMatches(query, page, controller.signal, date);
        if (!disposed) setResult({ key, data, error: null });
      } catch (error) {
        if (disposed) return;
        const message = timedOut ? 'The server took too long to respond. Try again.'
          : error instanceof Error && error.message.startsWith('The API') ? error.message
          : 'Could not load matches. Check the connection and try again.';
        setResult({ key, data: null, error: message });
      } finally {
        window.clearTimeout(timeout);
      }
    }, query ? 250 : 0);
    return () => {
      disposed = true;
      window.clearTimeout(debounce);
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [query, page, date, key]);

  const current = result?.key === key ? result : null;
  return {
    data: current?.data ?? null,
    error: current?.error ?? null,
    loading: current === null,
    retry: () => setAttempt((value) => value + 1),
  };
}
