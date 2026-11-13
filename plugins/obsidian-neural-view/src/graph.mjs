import {CATEGORIES} from './adapter.mjs';
export const MODULES = CATEGORIES.map(c => ({...c, kind: c.id}));
export const KINDS = Object.fromEntries(MODULES.map(c => [c.id, {label: c.title, en: c.en, color: c.color}]));
