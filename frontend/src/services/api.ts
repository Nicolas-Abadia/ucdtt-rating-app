// Every request uses the same build-time backend origin.
const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

export function apiUrl(path: string) {
  return `${baseUrl}${path}`;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number) {
    super(`Request failed with status ${status}`);
    this.name = 'ApiError';
    this.status = status;
  }
}

export async function getJson(path: string, signal: AbortSignal): Promise<unknown> {
  const response = await fetch(apiUrl(path), { signal, headers: { Accept: 'application/json' } });
  if (!response.ok) throw new ApiError(response.status);
  return response.json();
}
