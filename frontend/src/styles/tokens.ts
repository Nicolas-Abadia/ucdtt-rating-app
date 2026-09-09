// JS selects a token; CSS owns every color value.
export const AVATAR_COLORS = [
  'var(--night-sky-blue)',
  'var(--blood-red)',
  'var(--evening-purple)',
  'var(--arb-grass-green)',
  'var(--chetto-yellow)',
] as const;
export type AvatarColor = typeof AVATAR_COLORS[number];
