import { useEffect, useRef, useState } from 'react';
import { ApiError } from '../services/api';
import { authFetch } from '../services/auth';
import useMagneticDock from '../services/useMagneticDock';
import Icon from './Icon';
import styles from './NavigationMenu.module.css';

const COLLAPSE_DELAY_MS = 500;
const DOCK_HOVERED_CLASS = 'is-dock-hovered';

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
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
  if (context === 'player' && resourceId !== undefined) {
    return <>
      <a href={`#players/${resourceId}/edit`} className={styles.action}><Icon name="edit" />Edit player</a>
      <button type="button" className={`${styles.action} ${styles.dangerAction}`} onClick={onRequestDelete}>
        <Icon name="trash" />Delete player
      </button>
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
      <a href="#players/new" className={styles.action}><Icon name="plus" />Add new player</a>
    )}
    <a href={activePage === 'matches' ? '#import/matches' : '#import'} className={styles.action}><Icon name="upload" />Import CSV</a>
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

  useMagneticDock(dockRef);

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

  const deleteConfig = officerResourceId === undefined ? null
    : officerContext === 'match'
      ? {
        endpoint: `/api/matches/${officerResourceId}/`,
        label: 'Confirm delete match',
        successHash: '#matches',
        gone: 'This match no longer exists.',
      }
      : officerContext === 'player'
        ? {
          endpoint: `/api/players/${officerResourceId}/`,
          label: 'Confirm delete player',
          successHash: '#leaderboard',
          gone: 'This player no longer exists.',
        }
        : null;

  async function deleteResource() {
    if (!deleteConfig) return;
    clearCollapseTimer();
    setDeleting(true);
    setDeleteError(null);
    try {
      const response = await authFetch(deleteConfig.endpoint, { method: 'DELETE' });
      if (response.status === 204) {
        window.location.hash = deleteConfig.successHash;
        return;
      }
      if (response.status === 401 || response.status === 403) {
        setDeleteError('Your officer session expired. Log in again before deleting.');
      } else if (response.status === 404) {
        setDeleteError(deleteConfig.gone);
      } else {
        // A protected player comes back as 409 with an explanatory detail.
        let message = 'The server could not delete this record. Try again.';
        try {
          const body: unknown = await response.json();
          if (record(body) && typeof body.detail === 'string') message = body.detail;
        } catch { /* keep the generic message */ }
        setDeleteError(message);
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
      aria-label={confirmingDelete ? 'Delete confirmation' : 'Main navigation'}
      onMouseEnter={() => { document.body.classList.add(DOCK_HOVERED_CLASS); clearCollapseTimer(); }}
      onMouseLeave={() => {
        document.body.classList.remove(DOCK_HOVERED_CLASS);
        if (!deleting && expanded) scheduleCollapse();
      }}>
      {confirmingDelete ? (
        <div className={styles.deleteConfirmation}>
          {deleteError && <p className={styles.confirmationError} role="alert">{deleteError}</p>}
          <button ref={confirmDeleteRef} type="button" className={styles.confirmDelete}
            disabled={deleting} onClick={deleteResource}>
            <span>{deleting ? 'Deleting…' : (deleteConfig?.label ?? 'Confirm delete')}</span>
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
