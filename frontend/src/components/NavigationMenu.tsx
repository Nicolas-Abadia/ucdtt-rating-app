import { useEffect, useRef, useState } from 'react';
import { ApiError } from '../services/api';
import { authFetch } from '../services/auth';
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
  officerResourceId?: number;
  primaryAction?: NavigationPrimaryAction;
}

// A single confirmation action that replaces the dock's normal content (the
// login submit on the account page, for example). The dock breathes and glows
// with the action's accent color while the action is ready.
export interface NavigationPrimaryAction {
  label: string;
  activeLabel: string;
  accent: 'gold' | 'blue';
  disabled: boolean;
  busy: boolean;
  form?: string;
  onClick?: () => void;
}

function OfficerActions({ activePage, context, resourceId, onRequestDelete }: {
  activePage: 'leaderboard' | 'matches';
  context?: 'player' | 'match';
  resourceId?: number;
  onRequestDelete: () => void;
}) {
  if (context === 'player') {
    return <>
      <button type="button" disabled className={styles.action}><Icon name="edit" />Edit player <small>Coming soon</small></button>
      <button type="button" disabled className={`${styles.action} ${styles.dangerAction}`}><Icon name="trash" />Delete player <small>Coming soon</small></button>
    </>;
  }
  if (context === 'match' && resourceId !== undefined) {
    return <>
      <a href={`#matches/${resourceId}/edit`} className={styles.action}><Icon name="edit" />Edit match</a>
      <button type="button" className={`${styles.action} ${styles.dangerAction}`} onClick={onRequestDelete}>
        <Icon name="trash" />Delete match
      </button>
    </>;
  }
  return <>
    {activePage === 'matches' ? (
      <a href="#matches/new" className={styles.action}><Icon name="plus" />Log new match</a>
    ) : (
      <button type="button" disabled className={styles.action}><Icon name="plus" />Add new player <small>Coming soon</small></button>
    )}
    <button type="button" disabled className={styles.action}><Icon name="upload" />Import CSV <small>Coming soon</small></button>
  </>;
}

// Page actions live here, never in the account control. Destructive actions
// replace the whole dock with a second, explicit confirmation action rather
// than navigating to a separate confirmation page.
export default function NavigationMenu({ activePage = 'leaderboard', isOfficer = false, officerContext, officerResourceId, primaryAction }: NavigationMenuProps) {
  const [expanded, setExpanded] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const confirmDeleteRef = useRef<HTMLButtonElement>(null);
  const dockRef = useRef<HTMLElement>(null);
  const collapseTimerRef = useRef<number | null>(null);

  function clearCollapseTimer() {
    if (collapseTimerRef.current !== null) {
      window.clearTimeout(collapseTimerRef.current);
      collapseTimerRef.current = null;
    }
  }

  function closeDock() {
    setExpanded(false);
    setConfirmingDelete(false);
    setDeleteError(null);
  }

  function scheduleCollapse() {
    clearCollapseTimer();
    collapseTimerRef.current = window.setTimeout(closeDock, COLLAPSE_DELAY_MS);
  }

  function requestDelete() {
    clearCollapseTimer();
    setExpanded(false);
    setDeleteError(null);
    setConfirmingDelete(true);
  }

  async function deleteMatch() {
    if (officerResourceId === undefined) return;
    clearCollapseTimer();
    setDeleting(true);
    setDeleteError(null);
    try {
      const response = await authFetch(`/api/matches/${officerResourceId}/`, { method: 'DELETE' });
      if (response.status === 204) {
        window.location.hash = '#matches';
        return;
      }
      if (response.status === 401 || response.status === 403) {
        setDeleteError('Your officer session expired. Log in again before deleting.');
      } else if (response.status === 404) {
        setDeleteError('This match no longer exists.');
      } else {
        setDeleteError('The server could not delete this match. Try again.');
      }
    } catch (caught) {
      setDeleteError(caught instanceof ApiError && caught.status === 401
        ? 'Your officer session expired. Log in again before deleting.'
        : 'Could not reach the server. Check the connection and try again.');
    } finally {
      setDeleting(false);
    }
  }

  useEffect(() => {
    if (isOfficer) return;

    if (collapseTimerRef.current !== null) {
      window.clearTimeout(collapseTimerRef.current);
      collapseTimerRef.current = null;
    }

    // isOfficer=false starts the CSS shrink immediately. Reset retained state
    // one frame later so the next officer session starts collapsed.
    const frame = window.requestAnimationFrame(() => {
      setExpanded(false);
      setConfirmingDelete(false);
      setDeleteError(null);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [isOfficer]);

  useEffect(() => {
    if (confirmingDelete) confirmDeleteRef.current?.focus();
  }, [confirmingDelete]);

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
    if (!isOfficer || (!expanded && !confirmingDelete)) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Escape' || deleting) return;
      clearCollapseTimer();
      closeDock();
      toggleRef.current?.focus();
    }
    function onPointerDown(event: PointerEvent) {
      if (!deleting && !dockRef.current?.contains(event.target as Node)) {
        clearCollapseTimer();
        closeDock();
      }
    }
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('pointerdown', onPointerDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('pointerdown', onPointerDown);
    };
  }, [confirmingDelete, deleting, expanded, isOfficer]);

  const activeAccent = confirmingDelete ? 'red' : primaryAction?.accent;
  const attention = confirmingDelete
    ? !deleting
    : primaryAction !== undefined && !primaryAction.disabled && !primaryAction.busy;

  return (
    <nav ref={dockRef}
      className={`${styles.dock} ${isOfficer ? styles.officerDock : styles.publicDock} ${isOfficer && expanded ? styles.expanded : ''} ${attention ? styles.attention : ''}`}
      data-accent={activeAccent}
      aria-label={confirmingDelete ? 'Delete match confirmation' : 'Main navigation'}
      onMouseEnter={() => { document.body.classList.add(DOCK_HOVERED_CLASS); clearCollapseTimer(); }}
      onMouseLeave={() => {
        document.body.classList.remove(DOCK_HOVERED_CLASS);
        if (!deleting && expanded) scheduleCollapse();
      }}>
      {confirmingDelete ? (
        <div className={styles.deleteConfirmation}>
          {deleteError && <p className={styles.confirmationError} role="alert">{deleteError}</p>}
          <button ref={confirmDeleteRef} type="button" className={styles.confirmDelete}
            disabled={deleting} onClick={deleteMatch}>
            <span>{deleting ? 'Deleting…' : 'Confirm delete match'}</span>
            <Icon name="arrow" size={24} />
          </button>
        </div>
      ) : primaryAction ? (
        <div className={styles.primaryActionWrap}>
          <button type={primaryAction.form ? 'submit' : 'button'} form={primaryAction.form}
            className={`${styles.primaryAction} ${primaryAction.accent === 'blue' ? styles.primaryBlue : ''}`}
            disabled={primaryAction.disabled || primaryAction.busy} onClick={primaryAction.onClick}>
            <span>{primaryAction.busy ? primaryAction.activeLabel : primaryAction.label}</span>
            <Icon name="arrow" size={24} />
          </button>
        </div>
      ) : (
        <>
          <div id="navigation-options" className={styles.actions} aria-hidden={!isOfficer || !expanded}>
            <div className={styles.actionsInner}>
              <OfficerActions activePage={activePage} context={officerContext}
                resourceId={officerResourceId} onRequestDelete={requestDelete} />
            </div>
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
        </>
      )}
    </nav>
  );
}
