// JS selects a token; CSS owns every color value.
export const AVATAR_COLORS = [
  'var(--night-sky-blue)',
  'var(--blood-red)',
  'var(--evening-purple)',
  'var(--arb-grass-green)',
  'var(--chetto-yellow)',
] as const;
export type AvatarColor = typeof AVATAR_COLORS[number];

// Deterministic color from a name, for identities without a player id yet
// (officer avatar, add-player and import previews). Player cards color by id.
export function nameColorIndex(name: string): number {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) | 0;
  }
  return Math.abs(hash) % AVATAR_COLORS.length;
}
