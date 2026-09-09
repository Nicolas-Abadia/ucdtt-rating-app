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
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [open]);

  return (
    <header className={styles.header}>
      <h1 className={styles.title}>{title}</h1>
      <div className={styles.accountMenu}>
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
