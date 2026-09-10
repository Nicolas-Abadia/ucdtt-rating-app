import type { ReactNode } from 'react';
import Header from './Header';
import NavigationMenu from './NavigationMenu';
import { useAuth } from '../services/auth';
import styles from './PageLayout.module.css';

interface PageLayoutProps {
  title: string;
  activePage: 'leaderboard' | 'matches';
  children: ReactNode;
  backLabel?: string;
  backHash?: string;
  // Page actions belong to the navigation dock, not the account control.
  officerContext?: 'player' | 'match';
}

export default function PageLayout({ title, activePage, children, backLabel, backHash, officerContext }: PageLayoutProps) {
  const { username } = useAuth();
  const isOfficer = username !== null;
  return (
    <div id={activePage} className={styles.page}>
      <Header title={title} backLabel={backLabel} backHash={backHash} />
      <main className={styles.main}>{children}</main>
      <NavigationMenu activePage={activePage} isOfficer={isOfficer} officerContext={officerContext} />
    </div>
  );
}
