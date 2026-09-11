import type { CSSProperties } from 'react';
import Icon from './Icon';
import { useAuth } from '../services/auth';
import { AVATAR_COLORS, nameColorIndex } from '../styles/tokens';
import styles from './Header.module.css';

interface HeaderProps {
  title: string;
  backLabel?: string;
  backHash?: string;
}

// The account control is navigation only. The logged-out hamburger remains
// viewport-fixed; the logged-in officer avatar sits in the header and scrolls
// away with it. Both states link to the account page, the single home for
// login, session status and logout.
export default function Header({ title, backLabel, backHash }: HeaderProps) {
  const { username } = useAuth();
  const colorIndex = username ? nameColorIndex(username) : 0;
  const avatarStyle = {
    '--avatar-bg': AVATAR_COLORS[colorIndex],
    '--avatar-ink': colorIndex >= 3 ? 'var(--tone-black)' : 'var(--white)',
  } as CSSProperties;

  return (
    <header className={styles.header}>
      <div className={styles.titleGroup}>
        {backHash && (
          <a href={backHash} className={styles.backLink}>
            <Icon name="back" size={18} />
            <span>{backLabel ?? 'Back'}</span>
          </a>
        )}
        <h1 className={styles.title} tabIndex={-1}>{title}</h1>
      </div>

      <a
        href="#login"
        className={`${styles.accountLink} ${username ? styles.officerLink : styles.menuLink}`}
        aria-label={username ? `Open account page, logged in as ${username}` : 'Officer login'}
      >
        {username ? (
          <span key={username} className={styles.officerAvatar} style={avatarStyle} aria-hidden="true">
            {username.trim().charAt(0).toUpperCase()}
          </span>
        ) : (
          <Icon name="menu" size={24} />
        )}
      </a>
    </header>
  );
}
