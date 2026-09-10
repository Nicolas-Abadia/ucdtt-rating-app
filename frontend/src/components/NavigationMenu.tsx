import { useEffect, useRef, useState } from 'react';
import Icon from './Icon';
import styles from './NavigationMenu.module.css';

const COLLAPSE_DELAY_MS = 500;
// Plain global class name (not a CSS-module class) so it can be shared with
// the global stylesheet without hashing.
const DOCK_HOVERED_CLASS = 'is-dock-hovered';

// Re-checked on every pointer event rather than once on mount, so magnetism
// turns off immediately if the viewport becomes touch-driven. Touch is
// detected per event (pointerType) instead of ontouchstart/maxTouchPoints,
// which also report true on touch-capable laptops using a real mouse.
function isMagnetEligible() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return false;
  if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return false;
  if (window.innerWidth < 768) return false;
  return true;
}

// Public navigation has only two destinations. Officer controls require a
// confirmed auth state supplied by the caller; public is the safe default.
// This UI gate does not replace server-side authorization.
export default function NavigationMenu({ activePage = 'leaderboard', isOfficer = false }: {
  activePage?: 'leaderboard' | 'matches';
  isOfficer?: boolean;
}) {
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

  useEffect(() => () => {
    clearCollapseTimer();
    document.body.classList.remove(DOCK_HOVERED_CLASS);
  }, []);

  // Weak magnetic follow: the dock drifts a few px toward the cursor with a
  // lerped delay.
  useEffect(() => {
    const dock = dockRef.current;
    if (!dock) return;

    const RANGE = 120; // px beyond the dock where attraction starts
    const MAX = 8; // px maximum drift
    const LERP = 0.1; // lower = more delay
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

    function onPointerMove(e: PointerEvent) {
      // Mobile emulation and real touch devices emit touch pointers; only a
      // real mouse may pull the dock.
      if (e.pointerType !== 'mouse') return;
      if (!isMagnetEligible()) {
        targetX = 0;
        targetY = 0;
        if (!raf) raf = requestAnimationFrame(tick);
        return;
      }
      const rect = dock!.getBoundingClientRect();
      const dx = e.clientX - (rect.left + rect.width / 2);
      const dy = e.clientY - (rect.top + rect.height / 2);
      const dist = Math.hypot(dx, dy) || 1;
      const threshold = RANGE + Math.max(rect.width, rect.height) / 2;
      if (dist < threshold) {
        const strength = 1 - dist / threshold;
        targetX = (dx / dist) * MAX * strength;
        targetY = (dy / dist) * MAX * strength;
      } else {
        targetX = 0;
        targetY = 0;
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
    // pointerdown (not click) also catches the touch contact that starts a
    // scroll, so the dock collapses as soon as the page is scrolled away.
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
    <nav
      ref={dockRef}
      className={`${styles.dock} ${isOfficer && expanded ? styles.expanded : ''} ${!isOfficer ? styles.publicDock : ''}`}
      aria-label="Main navigation"
      onMouseEnter={() => {
        document.body.classList.add(DOCK_HOVERED_CLASS);
        clearCollapseTimer();
      }}
      onMouseLeave={() => {
        document.body.classList.remove(DOCK_HOVERED_CLASS);
        if (isOfficer && expanded) scheduleCollapse();
      }}
    >
      {isOfficer && <div id="navigation-options" className={styles.actions} aria-hidden={!expanded}>
        <div className={styles.actionsInner}>
          <button type="button" disabled className={styles.action}><Icon name="plus" />{activePage === 'matches' ? 'Log new match' : 'Add new player'} <small>Coming soon</small></button>
          <button type="button" disabled className={styles.action}><Icon name="upload" />Import CSV <small>Coming soon</small></button>
        </div>
      </div>}
      <div className={styles.destinations}>
        <a className={styles.leaderboard} href="#leaderboard" aria-current={activePage === 'leaderboard' ? 'page' : undefined} aria-label="Leaderboard">
          <span className={styles.destinationLabel}>
            <span>Leader</span><span>board</span>
          </span>
        </a>
        <a className={styles.matches} href="#matches" aria-current={activePage === 'matches' ? 'page' : undefined} aria-label="Match History">
          <span className={styles.destinationLabel}>
            <span>Match</span>{' '}<span>History</span>
          </span>
        </a>
        {isOfficer && <button
          ref={toggleRef}
          type="button"
          className={styles.toggle}
          onClick={() => {
            clearCollapseTimer();
            setExpanded(!expanded);
          }}
          aria-label={expanded ? 'Collapse navigation options' : 'Expand navigation options'}
          aria-controls="navigation-options"
          aria-expanded={expanded}
        >
          <Icon name={expanded ? 'close' : 'more'} size={28} />
        </button>}
      </div>
    </nav>
  );
}
