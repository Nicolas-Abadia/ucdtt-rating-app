import type { ReactNode } from 'react';
import Header from './Header';
import NavigationMenu from './NavigationMenu';
import styles from './PageLayout.module.css';

interface PageLayoutProps {
  title: string;
  activePage: 'leaderboard' | 'matches';
  children: ReactNode;
  // Set only from confirmed officer authentication, never a URL/storage flag.
  isOfficer?: boolean;
  // Detail pages pass a deterministic back destination; list pages omit it.
  backLabel?: string;
  backHash?: string;
}

export default function PageLayout({ title, activePage, children, isOfficer = false, backLabel, backHash }: PageLayoutProps) {
  return (
    <div id={activePage} className={styles.page}>
      <Header title={title} backLabel={backLabel} backHash={backHash} />
      <main className={styles.main}>{children}</main>
      <NavigationMenu key={isOfficer ? 'officer' : 'public'} activePage={activePage} isOfficer={isOfficer} />
    </div>
  );
}
