import { useEffect, useState } from 'react';
import { flushSync } from 'react-dom';

export interface Route {
  view: string;
  arg: string;
  /** Raw hash query (without `?`). URLSearchParams decodes values once, not the whole hash. */
  query: string;
}

/**
 * `#/view/path?query`. The query is split before decoding so an encoded
 * `%26` or `%2F` keeps its meaning as data inside a single query value.
 */
export function parseRoute(hash: string): Route {
  const raw = hash.replace(/^#\/?/, '');
  const split = raw.indexOf('?');
  const pathText = split === -1 ? raw : raw.slice(0, split);
  const query = split === -1 ? '' : raw.slice(split + 1);
  let segments: string[];
  try {
    segments = pathText.split('/').map((segment) => decodeURIComponent(segment));
  } catch {
    return { view: 'gallery', arg: '', query }; // a truncated or hand-typed %-sequence
  }
  const [view, ...rest] = segments;
  return { view: view || 'gallery', arg: rest.join('/'), query };
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(location.hash));
  useEffect(() => {
    // Committed synchronously so a running view transition captures the new page.
    const onChange = () => flushSync(() => setRoute(parseRoute(location.hash)));
    addEventListener('hashchange', onChange);
    return () => removeEventListener('hashchange', onChange);
  }, []);
  return route;
}
