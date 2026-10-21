import type { GraphData } from './api';

/**
 * The analysis → figure chains, read from the graph's `feeds` edges
 * (method → interface, interface → template, interface → method). Keys and values are page paths.
 */
export class Flow {
  private out = new Map<string, string[]>();
  private into = new Map<string, string[]>();

  constructor(graph: GraphData) {
    for (const { source, target, kind } of graph.links) {
      if (kind !== 'feeds') continue;
      this.out.set(source, [...(this.out.get(source) ?? []), target]);
      this.into.set(target, [...(this.into.get(target) ?? []), source]);
    }
  }

  /** Interfaces a method writes, or pages that read an interface. */
  outputs = (path: string) => this.out.get(path) ?? [];
  /** Interfaces a template or method reads, or methods that write an interface. */
  inputs = (path: string) => this.into.get(path) ?? [];

  /** Templates whose every input table is among the method's outputs, the same rule as the page facts. */
  figuresOf(method: string) {
    const made = new Set(this.outputs(method));
    const reached = new Set(this.outputs(method).flatMap(this.outputs).filter((p) => p.startsWith('templates/')));
    return [...reached].filter((t) => this.inputs(t).every((i) => made.has(i)));
  }

  /** Methods that can feed every input table of a template. */
  methodsFor(template: string) {
    const needs = this.inputs(template);
    const candidates = new Set(needs.flatMap(this.inputs));
    return [...candidates].filter((m) => this.figuresOf(m).includes(template));
  }
}
