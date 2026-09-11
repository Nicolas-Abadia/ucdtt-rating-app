import { useCallback, useSyncExternalStore } from 'react';

// Subscribe to a CSS media query with the same external-store pattern the rest
// of the app uses. The server snapshot is false so nothing that is
// desktop-only renders before hydration on a mobile device.
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback((callback: () => void) => {
    const mql = window.matchMedia(query);
    mql.addEventListener('change', callback);
    return () => mql.removeEventListener('change', callback);
  }, [query]);
  const getSnapshot = useCallback(() => window.matchMedia(query).matches, [query]);
  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}
