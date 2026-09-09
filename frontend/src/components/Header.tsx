import { useEffect, useRef, useState } from 'react';
import Icon from './Icon';
import styles from './Header.module.css';

interface HeaderProps {
  title: string;
}

// The header button is the account menu (login for now). Navigation options
// have their own toggle on the NavigationMenu dock.
export default function Header({ title }: HeaderProps) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const accountMenuRef = useRef<HTMLDivElement>(null);
  // Same-origin in production; the Vite dev proxy forwards /accounts to Django.
  const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false);
        buttonRef.current?.focus();
      }
    }
    // pointerdown (not click) also catches the touch contact that starts a
    // scroll, so the menu closes as soon as the page is scrolled away.
    function onPointerDown(event: PointerEvent) {
      if (!accountMenuRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('pointerdown', onPointerDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('pointerdown', onPointerDown);
    };
  }, [open]);

  return (
    <header className={styles.header}>
      <h1 className={styles.title}>{title}</h1>
      <div className={styles.accountMenu} ref={accountMenuRef}>
        <button
          ref={buttonRef}
          type="button"
          className={styles.menuButton}
          onClick={() => setOpen(!open)}
          aria-label="Account menu"
          aria-expanded={open}
          aria-haspopup="true"
        >
          <Icon name={open ? 'close' : 'menu'} size={24} />
        </button>
        {open && (
          <div className={styles.accountPanel}>
            <a href={`${baseUrl}/accounts/login/`} onClick={() => setOpen(false)}>Officer login</a>
          </div>
        )}
      </div>
    </header>
  );
}
