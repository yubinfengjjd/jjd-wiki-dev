import React from 'react';
import {createRoot} from 'react-dom/client';
import {NeuralApp} from '../src/ui/App.jsx';
import {readGraph, fallbackResolve} from '../src/adapter.mjs';
// Explicit isolated test fixture, never bundled into the Obsidian plugin.
const contents = {
  'layouts/fixture-layout.md': '# Fixture layout\n[[templates/fixture-template|Fixture template]]\n[[methods/fixture-method]]\n[[missing-note]]',
  'templates/fixture-template.md': '# Fixture template\n[[layouts/fixture-layout]]\n[[interfaces/fixture-interface]]',
  'methods/fixture-method.md': '# Fixture method\n[[interfaces/fixture-interface]]',
  'interfaces/fixture-interface.md': '# Fixture interface',
  'projects/fixture-project.md': '# Fixture project\n[[methods/fixture-method]]'
};
const files = Object.keys(contents).map(path => ({path, basename: path.split('/').at(-1).replace(/\.md$/, '')}));
const vault = {getMarkdownFiles: () => files, cachedRead: async file => contents[file.path], getAbstractFileByPath: () => null, adapter: {getResourcePath: path => path}};
const cache = {getFileCache: () => null, getFirstLinkpathDest: (link, source) => fallbackResolve(link, source, files)};
const media = Object.fromEntries(['orb.mp4','orb.jpg','jellyfish.mp4','jellyfish.jpg'].map(name => [name, `/media/${name}`]));
const root = createRoot(document.getElementById('root'));
readGraph(vault, cache).then(graph => root.render(<NeuralApp graph={graph} media={media} onOpen={path => {document.title = `Open note (fixture): ${path}`;}} onRefresh={() => {}}/>));
window.previewUnmount = () => root.unmount();
