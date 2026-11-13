import type { Compatibility, PageType, Status } from './api';

/**
 * Journal-figure palette. Green marks what is alive (chart-type hubs, usable items),
 * ochre marks what waits on the author, indigo what waits on an agent.
 * Methods are plum and interfaces slate, so an analysis chain reads as its own strand.
 * v2 recipes are teal; their source libraries muted squares, research scenarios green diamonds.
 * CSS declares the same values in styles.css; WebGL code reads them from here.
 */
export const INK = {
  paper: '#f7f8f6',
  ink: '#1f2a37',
  muted: '#5f6b78',
  line: '#9aa3ad',
  hub: '#2f8f5b',
  ochre: '#b5651d',
  indigo: '#3b5b8c',
  plum: '#7b3f73',
  slate: '#5d7a8c',
  faint: '#c4cad1',
  teal: '#2a6f77',
};

export const STATUS_COLOR: Record<Status, string> = {
  pending_signoff: INK.ochre,
  pending_template: INK.indigo,
  draft: INK.ochre,
  ready: INK.hub,
  archived: INK.faint,
};

export const COMPATIBILITY_COLOR: Record<Compatibility, string> = {
  direct: INK.hub,
  adaptable: INK.ochre,
  candidate: INK.slate,
};

export const TYPE_COLOR: Record<PageType, string> = {
  'chart-type': INK.hub,
  layout: INK.ink,
  template: INK.ink,
  method: INK.plum,
  interface: INK.slate,
  project: INK.indigo,
  recipe: INK.teal,
  source: INK.muted,
  scenario: INK.hub,
};

/** Node shapes in the graph shaders: 0 disc, 1 square, 2 diamond. */
export const TYPE_SHAPE: Record<PageType, number> = {
  'chart-type': 0,
  layout: 0,
  template: 0,
  method: 1,
  interface: 2,
  project: 0,
  recipe: 0,
  source: 1,
  scenario: 2,
};

/** Types whose node carries a status ring. */
export const HAS_STATUS = (type: PageType) =>
  type === 'layout' || type === 'template' || type === 'method' || type === 'recipe';

/** Hub pages: large green nodes with always-visible labels, which other pages cluster round. */
export const IS_HUB = (type: PageType) => type === 'chart-type';
