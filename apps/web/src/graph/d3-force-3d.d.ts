// Only the parts of d3-force-3d this app uses.
declare module 'd3-force-3d' {
  export interface SimNode {
    index?: number;
    x?: number;
    y?: number;
    z?: number;
    vx?: number;
    vy?: number;
    vz?: number;
    fx?: number | null;
    fy?: number | null;
    fz?: number | null;
  }

  export interface SimLink<N extends SimNode> {
    source: N | string;
    target: N | string;
  }

  export interface Force<N extends SimNode> {
    (alpha: number): void;
  }

  export interface Simulation<N extends SimNode> {
    nodes(): N[];
    nodes(nodes: N[]): this;
    numDimensions(n: 1 | 2 | 3): this;
    alpha(): number;
    alpha(value: number): this;
    alphaTarget(value: number): this;
    alphaDecay(value: number): this;
    velocityDecay(value: number): this;
    force(name: string, force: Force<N> | null): this;
    tick(iterations?: number): this;
    stop(): this;
  }

  export interface LinkForce<N extends SimNode> extends Force<N> {
    id(fn: (node: N) => string): this;
    distance(fn: number | ((link: SimLink<N>) => number)): this;
    strength(fn: number | ((link: SimLink<N>) => number)): this;
  }

  export interface ManyBodyForce<N extends SimNode> extends Force<N> {
    strength(fn: number | ((node: N) => number)): this;
    distanceMax(value: number): this;
  }

  export interface CollideForce<N extends SimNode> extends Force<N> {
    radius(fn: number | ((node: N) => number)): this;
  }

  export interface CenterForce<N extends SimNode> extends Force<N> {
    strength(value: number): this;
  }

  export function forceSimulation<N extends SimNode>(nodes: N[], numDimensions?: number): Simulation<N>;
  export function forceLink<N extends SimNode>(links: SimLink<N>[]): LinkForce<N>;
  export function forceManyBody<N extends SimNode>(): ManyBodyForce<N>;
  export function forceCollide<N extends SimNode>(): CollideForce<N>;
  export function forceCenter<N extends SimNode>(): CenterForce<N>;
}
