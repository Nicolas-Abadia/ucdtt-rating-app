import { useEffect } from 'react';
import type { RefObject } from 'react';

function isMagnetEligible() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return false;
  if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return false;
  if (window.innerWidth < 768) return false;
  return true;
}

// Shared magnetic drift for the fixed docks. The element eases a few px toward
// the cursor on fine-pointer desktop viewports. Components expose --magnet-x
// and --magnet-y inside their own transform (and any transform animation), so
// the drift composes with breathing or hover motion instead of replacing it.
export default function useMagneticDock(ref: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    // Bound once as non-nullable: the closures below outlive the guard.
    const dock: HTMLElement = element;
    const RANGE = 120;
    const MAX = 8;
    const LERP = 0.1;
    let targetX = 0, targetY = 0, currentX = 0, currentY = 0;
    let raf = 0;

    function tick() {
      currentX += (targetX - currentX) * LERP;
      currentY += (targetY - currentY) * LERP;
      const settled = targetX === 0 && targetY === 0 && Math.abs(currentX) < 0.1 && Math.abs(currentY) < 0.1;
      dock.style.setProperty('--magnet-x', `${currentX.toFixed(2)}px`);
      dock.style.setProperty('--magnet-y', `${currentY.toFixed(2)}px`);
      raf = settled ? 0 : requestAnimationFrame(tick);
    }

    function onPointerMove(event: PointerEvent) {
      if (event.pointerType !== 'mouse') return;
      if (!isMagnetEligible()) {
        targetX = 0; targetY = 0;
        if (!raf) raf = requestAnimationFrame(tick);
        return;
      }
      const rect = dock.getBoundingClientRect();
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
  }, [ref]);
}
