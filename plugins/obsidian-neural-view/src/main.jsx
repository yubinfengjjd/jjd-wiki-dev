import React from 'react';
import {createRoot} from 'react-dom/client';
import {ItemView, Plugin, Notice, TFile} from 'obsidian';
import {NeuralApp} from './ui/App.jsx';
import {readGraph} from './adapter.mjs';
import {openExistingNote} from './native-open.mjs';

const VIEW = 'research-wiki-neural-view';
export class NeuralView extends ItemView {
  constructor(leaf, plugin) { super(leaf); this.plugin = plugin; this.version = 0; this.closed = false; }
  getViewType() { return VIEW; }
  getDisplayText() { return '科研知识库 · 神经图谱'; }
  getIcon() { return 'network'; }
  async onOpen() {
    this.closed = false;
    this.contentEl.empty();
    this.contentEl.addClass('research-neural-view');
    this.contentEl.tabIndex = 0;
    this.root = createRoot(this.contentEl);
    this.observer = new IntersectionObserver(entries => {
      this.hidden = !entries.some(entry => entry.isIntersecting);
      this.render();
    });
    this.observer.observe(this.contentEl);
    const refresh = () => {
      window.clearTimeout(this.refreshTimer);
      this.refreshTimer = window.setTimeout(() => this.refresh(), 180);
    };
    this.eventRefs = [];
    const subscribe = (emitter, event) => {
      const reference = emitter.on(event, refresh);
      this.eventRefs.push([emitter, reference]);
      this.registerEvent(reference);
    };
    subscribe(this.app.metadataCache, 'resolved');
    subscribe(this.app.metadataCache, 'changed');
    for (const event of ['create', 'delete', 'rename', 'modify']) subscribe(this.app.vault, event);
    await this.refresh();
  }
  async refresh() {
    const version = ++this.version;
    try {
      const graph = await readGraph(this.app.vault, this.app.metadataCache);
      if (this.closed || version !== this.version) return;
      this.graph = graph;
      this.error = null;
    } catch (error) { if (this.closed || version !== this.version) return; this.error = String(error); }
    this.render();
  }
  render() {
    if (!this.root || this.closed) return;
    if (!this.graph) { this.root.render(<div className="neural-message">{this.error ? `读取失败：${this.error}` : '正在读取本地知识库…'}</div>); return; }
    const media = Object.fromEntries(['orb.mp4', 'orb.jpg', 'jellyfish.mp4', 'jellyfish.jpg'].map(name => [name, this.app.vault.adapter.getResourcePath(`${this.plugin.manifest.dir}/media/${name}`)]));
    this.root.render(<NeuralApp graph={this.graph} media={media} hidden={this.hidden} error={this.error}
      onRefresh={() => this.refresh()} onOpen={async path => {
        // Always use an exact, already indexed path. Unresolved links never create blank notes.
        if (!this.graph.index.has(path)) return;
        try {
          if (!await openExistingNote(this.app, path, file => file instanceof TFile)) {
            new Notice('笔记已删除、移动或暂不可用，请刷新图谱。');
            this.refresh();
          }
        }
        catch (error) { new Notice(`无法打开笔记：${String(error)}`); }
      }}/>);
  }
  async onClose() {
    this.closed = true; this.version++;
    window.clearTimeout(this.refreshTimer);
    for (const [emitter, reference] of this.eventRefs || []) emitter.offref(reference);
    this.eventRefs = [];
    this.observer?.disconnect();
    this.root?.unmount(); this.root = null;
    this.contentEl.empty();
  }
}
export default class NeuralPlugin extends Plugin {
  async onload() {
    this.registerView(VIEW, leaf => new NeuralView(leaf, this));
    this.addRibbonIcon('network', '打开科研神经图谱', () => this.activate());
    this.addCommand({id: 'open-research-neural-view', name: '打开科研神经图谱 / Open research neural view', callback: () => this.activate()});
    this.addCommand({id: 'refresh-research-neural-view', name: '刷新科研神经图谱 / Refresh research neural view', callback: () => this.app.workspace.getLeavesOfType(VIEW).forEach(leaf => leaf.view.refresh())});
    // Preserve the user's saved leaves and focus; only an empty workspace opens automatically.
    this.app.workspace.onLayoutReady(() => {
      const populated = [];
      this.app.workspace.iterateAllLeaves(leaf => { if (leaf.view.getViewType() !== 'empty') populated.push(leaf); });
      if (!populated.length) this.activate();
    });
  }
  async activate() {
    let leaf = this.app.workspace.getLeavesOfType(VIEW)[0];
    if (!leaf) { leaf = this.app.workspace.getLeaf('tab'); await leaf.setViewState({type: VIEW, active: true}); }
    await this.app.workspace.revealLeaf(leaf);
  }
  onunload() { this.app.workspace.detachLeavesOfType(VIEW); }
}
