import { useEffect } from 'react';
import { FlowField } from './FlowField';

export const backdrop = new FlowField(document.getElementById('backdrop') as HTMLCanvasElement);

const GALLERY_HERO = 420;

/**
 * Background intensity by zone: strong over the gallery hero, fainter over the plate
 * grid and page text, faintest behind the knowledge network so nodes stay legible.
 */
export function useBackdropZone(view: string) {
  useEffect(() => {
    backdrop.setPaused(view === 'search' || view === 'page');
    const update = () => {
      if (view === 'gallery') backdrop.setIntensity(scrollY < GALLERY_HERO ? 1 : 0.75);
      else if (view === 'graph') backdrop.setIntensity(0.45);
      else if (view === 'page') backdrop.setIntensity(0.65);
      else backdrop.setIntensity(0.85);
    };
    update();
    addEventListener('scroll', update, { passive: true });
    return () => removeEventListener('scroll', update);
  }, [view]);
}
