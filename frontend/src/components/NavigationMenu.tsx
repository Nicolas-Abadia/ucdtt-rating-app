import { useEffect, useRef, useState } from 'react';
import Icon from './Icon';
import styles from './NavigationMenu.module.css';

const COLLAPSE_DELAY_MS = 500;
const DOCK_HOVERED_CLASS = 'is-dock-hovered';

function isMagnetEligible() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return false;
  if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return false;
  if (window.innerWidth < 768) return false;
  return true;
}

interface NavigationMenuProps {
  activePage?: 'leaderboard' | 'matches';
  isOfficer?: boolean;
  officerContext?: 'player' | 'match';
}

function OfficerActions({ activePage, context }: { activePage: 'leaderboard' | 'matches'; context?: 'player' | 'match' }) {
  if (context === 'player') {
    return <>
      <button type="button" disabled className={styles.action}><Icon name="edit" />Edit player <small>Coming soon</small></button>
      <button type="button" disabled className={`${styles.action} ${styles.dangerAction}`}><Icon name="trash" />Delete player <small>Coming soon</small></button>
    </>;
  }
  if (context === 'match') {
    return <>
      <button type="button" disabled className={styles.action}><Icon name="edit" />Edit match <small>Coming soon</small></button>
      <button type="button" disabled className={`${styles.action} ${styles.dangerAction}`}><Icon name="trash" />Delete match <small>Coming soon</small></button>
    </>;
  }
  return <>
    <button type="button" disabled className={styles.action}><Icon name="plus" />{activePage === 'matches' ? 'Log new match' : 'Add new player'} <small>Coming soon</small></button>
    <button type="button" disabled className={styles.action}><Icon name="upload" />Import CSV <small>Coming soon</small></button>
  </>;
}

// Page actions live here, never in the account control. The white toggle stays
// mounted through auth changes so it can bubble down while its grid track
// closes on logout, leaving the two-destination public dock.
export default function NavigationMenu({ activePage = 'leaderboard', isOfficer = false, officerContext }: NavigationMenuProps) {
  const [expanded, setExpanded] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const dockRef = useRef<HTMLElement>(null);
  const collapseTimerRef = useRef<number | null>(null);

  function clearCollapseTimer() {
    if (collapseTimerRef.current !== null) {
      window.clearTimeout(collapseTimerRef.current);
      collapseTimerRef.current = null;
    }
  }
  function scheduleCollapse() {
    clearCollapseTimer();
    collapseTimerRef.current = window.setTimeout(() => setExpanded(false), COLLAPSE_DELAY_MS);
  }

  useEffect(() => {
    if (isOfficer) return;

    if (collapseTimerRef.current !== null) {
      window.clearTimeout(collapseTimerRef.current);
      collapseTimerRef.current = null;
    }

    // isOfficer=false starts the CSS shrink immediately. Reset the retained
    // state one frame later so the next officer session starts collapsed.
    const frame = window.requestAnimationFrame(() => setExpanded(false));
    return () => window.cancelAnimationFrame(frame);
  }, [isOfficer]);

  useEffect(() => () => {
    clearCollapseTimer();
    document.body.classList.remove(DOCK_HOVERED_CLASS);
  }, []);

  useEffect(() => {
    const dock = dockRef.current;
    if (!dock) return;
    const RANGE = 120;
    const MAX = 8;
    const LERP = 0.1;
    let targetX = 0, targetY = 0, currentX = 0, currentY = 0;
    let raf = 0;

    function tick() {
      currentX += (targetX - currentX) * LERP;
      currentY += (targetY - currentY) * LERP;
      const settled = targetX === 0 && targetY === 0 && Math.abs(currentX) < 0.1 && Math.abs(currentY) < 0.1;
      dock!.style.setProperty('--magnet-x', `${currentX.toFixed(2)}px`);
      dock!.style.setProperty('--magnet-y', `${currentY.toFixed(2)}px`);
      raf = settled ? 0 : requestAnimationFrame(tick);
    }

    function onPointerMove(event: PointerEvent) {
      if (event.pointerType !== 'mouse') return;
      if (!isMagnetEligible()) {
        targetX = 0; targetY = 0;
        if (!raf) raf = requestAnimationFrame(tick);
        return;
      }
      const rect = dock!.getBoundingClientRect();
      const dx = event.clientX - (rect.left + rect.width / 2);
      const dy = event.clientY - (rect.top + rect.height / 2);
      const dist = Math.hypot(dx, dy) || 1;
      const threshold = RANGE + Math.max(rect.width, rect.height) / 2;
      if (dist < threshold) {
        const strength = 1 - dist / threshold;
        targetX = (dx / dist) * MAX * strength;
        targetY = (dy / dist) * MAX * strength;
      } else {
        targetX = 0; targetY = 0;
      }
      if (!raf) raf = requestAnimationFrame(tick);
    }

    window.addEventListener('pointermove', onPointerMove);
    return () => {
      window.removeEventListener('pointermove', onPointerMove);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  useEffect(() => {
    if (!isOfficer || !expanded) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        clearCollapseTimer();
        setExpanded(false);
        toggleRef.current?.focus();
      }
    }
    function onPointerDown(event: PointerEvent) {
      if (!dockRef.current?.contains(event.target as Node)) {
        clearCollapseTimer();
        setExpanded(false);
      }
    }
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('pointerdown', onPointerDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('pointerdown', onPointerDown);
    };
  }, [expanded, isOfficer]);

  return (
    <nav ref={dockRef}
      className={`${styles.dock} ${isOfficer ? styles.officerDock : styles.publicDock} ${isOfficer && expanded ? styles.expanded : ''}`}
      aria-label="Main navigation"
      onMouseEnter={() => { document.body.classList.add(DOCK_HOVERED_CLASS); clearCollapseTimer(); }}
      onMouseLeave={() => { document.body.classList.remove(DOCK_HOVERED_CLASS); if (isOfficer && expanded) scheduleCollapse(); }}>
      <div id="navigation-options" className={styles.actions} aria-hidden={!isOfficer || !expanded}>
        <div className={styles.actionsInner}><OfficerActions activePage={activePage} context={officerContext} /></div>
      </div>
      <div className={styles.destinations}>
        <a className={styles.leaderboard} href="#leaderboard" aria-current={activePage === 'leaderboard' ? 'page' : undefined} aria-label="Leaderboard">
          <span className={styles.destinationLabel}><span>Leader</span><span>board</span></span>
        </a>
        <a className={styles.matches} href="#matches" aria-current={activePage === 'matches' ? 'page' : undefined} aria-label="Match History">
          <span className={styles.destinationLabel}><span>Match</span>{' '}<span>History</span></span>
        </a>
        <div className={styles.toggleSlot} aria-hidden={!isOfficer}>
          <button ref={toggleRef} type="button" className={styles.toggle} disabled={!isOfficer}
            tabIndex={isOfficer ? 0 : -1}
            onClick={() => { clearCollapseTimer(); setExpanded((value) => !value); }}
            aria-label={expanded ? 'Collapse navigation options' : 'Expand navigation options'}
            aria-controls="navigation-options" aria-expanded={isOfficer && expanded}>
            <Icon name={expanded ? 'close' : 'more'} size={28} />
          </button>
        </div>
      </div>
    </nav>
  );
}
