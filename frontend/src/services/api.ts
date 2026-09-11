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

export function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

// DRF error bodies are { field: [messages] } or { detail: string }; this
// flattens any of those shapes to one message.
export function messageFrom(value: unknown): string | null {
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) {
    const messages = value.map(messageFrom).filter((item): item is string => item !== null);
    return messages.length ? messages.join(' ') : null;
  }
  return null;
}
