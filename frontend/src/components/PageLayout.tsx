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
  officerResourceId?: number;
  showOfficerActions?: boolean;
  showNavigation?: boolean;
}

export default function PageLayout({ title, activePage, children, backLabel, backHash,
  officerContext, officerResourceId, showOfficerActions = true, showNavigation = true }: PageLayoutProps) {
  const { username } = useAuth();
  const isOfficer = username !== null;
  return (
    <div id={activePage} className={styles.page}>
      <Header title={title} backLabel={backLabel} backHash={backHash} />
      <main className={styles.main}>{children}</main>
      {showNavigation && <NavigationMenu activePage={activePage} isOfficer={isOfficer && showOfficerActions}
        officerContext={officerContext} officerResourceId={officerResourceId} />}
    </div>
  );
}
