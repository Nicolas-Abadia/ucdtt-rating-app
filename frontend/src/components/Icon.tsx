type IconName = 'menu' | 'close' | 'search' | 'more' | 'plus' | 'upload' | 'rating' | 'win' | 'loss' | 'back' | 'edit' | 'trash' | 'user' | 'logout';

export default function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {name === 'menu' && <path d="M4 6h16M4 12h16M4 18h16" />}
      {name === 'close' && <path d="m6 6 12 12M6 18 18 6" />}
      {name === 'search' && <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4 4" /></>}
      {name === 'more' && <><circle cx="12" cy="5" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="12" cy="19" r="1" /></>}
      {name === 'plus' && <path d="M12 5v14M5 12h14" />}
      {name === 'upload' && <path d="M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6" />}
      {name === 'rating' && <path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9Z" />}
      {name === 'win' && <path d="m5 12 4 4L19 6" />}
      {name === 'loss' && <path d="m7 7 10 10M7 17 17 7" />}
      {name === 'back' && <path d="M15 5 8 12l7 7" />}
      {name === 'edit' && <path d="M17 3a2.8 2.8 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />}
      {name === 'trash' && <><path d="M3 6h18" /><path d="M8 6V4h8v2" /><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" /></>}
      {name === 'user' && <><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7" /></>}
      {name === 'logout' && <><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="m16 17 5-5-5-5" /><path d="M21 12H9" /></>}
    </svg>
  );
}
