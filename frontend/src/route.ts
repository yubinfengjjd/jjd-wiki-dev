import { useEffect, useState } from 'react';
import { flushSync } from 'react-dom';

export interface Route {
  view: string;
  arg: string;
}

function parse(hash: string): Route {
  let text: string;
  try {
    text = decodeURIComponent(hash.replace(/^#\/?/, ''));
  } catch {
    return { view: 'gallery', arg: '' }; // a truncated or hand-typed %-sequence
  }
  const [view, ...rest] = text.split('/');
  return { view: view || 'gallery', arg: rest.join('/') };
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parse(location.hash));
  useEffect(() => {
    // Committed synchronously so a running view transition captures the new page.
    const onChange = () => flushSync(() => setRoute(parse(location.hash)));
    addEventListener('hashchange', onChange);
    return () => removeEventListener('hashchange', onChange);
  }, []);
  return route;
}
