import { useEffect, useState } from 'react';
import { ApiError, getJson } from './api';

interface Result<T> {
  key: string;
  data: T | null;
  error: string | null;
  notFound: boolean;
}

// Generic single-resource fetch for detail pages. Parsers must be stable
// (module-scope functions), the same pattern useMatches/fetchMatches uses.
export default function useApiResource<T>(path: string, parse: (value: unknown) => T) {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<Result<T> | null>(null);
  const key = JSON.stringify([path, attempt]);

  useEffect(() => {
    const controller = new AbortController();
    let disposed = false;
    let timedOut = false;
    const timeout = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, 90000);
    (async () => {
      try {
        const data = parse(await getJson(path, controller.signal));
        if (!disposed) setResult({ key, data, error: null, notFound: false });
      } catch (error) {
        if (disposed) return;
        const notFound = error instanceof ApiError && error.status === 404;
        const message = timedOut ? 'The server took too long to respond. Try again.'
          : notFound ? 'Not found.'
          : error instanceof Error && error.message.startsWith('The API') ? error.message
          : 'Could not load this page. Check the connection and try again.';
        setResult({ key, data: null, error: message, notFound });
      } finally {
        window.clearTimeout(timeout);
      }
    })();
    return () => {
      disposed = true;
      window.clearTimeout(timeout);
      controller.abort();
    };
    // path change immediately invalidates the previous result via the key guard below.
  }, [path, parse, key]);

  const current = result?.key === key ? result : null;
  return {
    data: current?.data ?? null,
    error: current?.error ?? null,
    notFound: current?.notFound ?? false,
    loading: current === null,
    retry: () => setAttempt((value) => value + 1),
  };
}
