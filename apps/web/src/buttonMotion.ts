import { animate } from 'motion';

/*
 * Button feel, attached once by event delegation so every button in every view gets it:
 *  primary — ink spreads from where the pointer entered, the button leans towards the
 *            pointer (magnetic) and squashes on press with a spring;
 *  outline — CSS traces the border on hover (styles.css); a fine ripple spreads from the click;
 *  quiet   — small buttons, tabs, chips, link rows: colour change only.
 */

type Kind = 'primary' | 'outline';

const QUIET = '.small, .link-button, .chip, .turn, .tabs button';
const SPRING = { type: 'spring', stiffness: 320, damping: 18, mass: 0.6 } as const;
const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

function kindOf(target: EventTarget | null): [HTMLElement, Kind] | null {
  const el = (target as Element | null)?.closest?.<HTMLElement>('button, .button');
  if (!el || el.matches(QUIET) || el.matches(':disabled')) return null;
  return [el, el.matches('.primary') ? 'primary' : 'outline'];
}

/** Put the ink drop's centre at the pointer, sized to cover the button from there. */
function placeInk(el: HTMLElement, e: PointerEvent) {
  const r = el.getBoundingClientRect();
  const x = e.clientX - r.left;
  const y = e.clientY - r.top;
  const reach = Math.hypot(Math.max(x, r.width - x), Math.max(y, r.height - y));
  el.style.setProperty('--ix', `${x}px`);
  el.style.setProperty('--iy', `${y}px`);
  el.style.setProperty('--id', `${reach * 2}px`);
}

export function installButtonMotion() {
  addEventListener('pointerover', (e) => {
    const hit = kindOf(e.target);
    if (!hit || hit[1] !== 'primary' || hit[0].contains(e.relatedTarget as Node)) return;
    placeInk(hit[0], e);
    hit[0].classList.add('inked');
  });

  addEventListener('pointerout', (e) => {
    const hit = kindOf(e.target);
    if (!hit || hit[1] !== 'primary' || hit[0].contains(e.relatedTarget as Node)) return;
    placeInk(hit[0], e);
    hit[0].classList.remove('inked');
    if (!reduced()) animate(hit[0], { x: 0, y: 0, scale: 1 }, SPRING);
  });

  addEventListener('pointermove', (e) => {
    const hit = kindOf(e.target);
    if (!hit || hit[1] !== 'primary' || reduced()) return;
    const r = hit[0].getBoundingClientRect();
    const dx = (e.clientX - (r.left + r.width / 2)) * 0.22;
    const dy = (e.clientY - (r.top + r.height / 2)) * 0.32;
    animate(hit[0], { x: dx, y: dy }, SPRING);
  });

  addEventListener('pointerdown', (e) => {
    const hit = kindOf(e.target);
    if (!hit || reduced()) return;
    const [el, kind] = hit;
    if (kind === 'primary') {
      animate(el, { scale: 0.93 }, { duration: 0.08 });
      return;
    }
    const r = el.getBoundingClientRect();
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    ripple.style.left = `${e.clientX - r.left}px`;
    ripple.style.top = `${e.clientY - r.top}px`;
    ripple.style.setProperty('--rd', `${Math.hypot(r.width, r.height) * 2}px`);
    ripple.addEventListener('animationend', () => ripple.remove(), { once: true });
    el.append(ripple);
  });

  addEventListener('pointerup', (e) => {
    const hit = kindOf(e.target);
    if (hit?.[1] === 'primary' && !reduced()) animate(hit[0], { scale: 1 }, SPRING);
  });
}
