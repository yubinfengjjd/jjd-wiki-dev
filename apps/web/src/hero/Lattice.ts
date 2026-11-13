import * as THREE from 'three';
import type { GraphData, GraphNode } from '../api';
import { HAS_STATUS, INK, IS_HUB, STATUS_COLOR, TYPE_COLOR } from '../palette';

/*
 * The home page's model: the wiki's real pages arranged on a sphere like an
 * armillary/crystal model. Scenario hubs are spread evenly; every other page sits
 * near the hub it links to; links are arcs bowing outwards. Drawn in ink on paper,
 * with depth shown by fading the far side. On load, arcs draw themselves in.
 */

const R = 100;
const SEGMENTS = 24;
const REVEAL_MS = 2400;

const lineVertex = /* glsl */ `
  uniform float uProgress;
  uniform float uNear;
  uniform float uFocus;
  attribute float aT;
  attribute float aDelay;
  attribute float aBase;
  attribute vec2 aEnds;
  varying float vAlpha;
  varying float vT;
  varying float vReach;
  varying float vLit;

  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mv;
    float front = 1.0 - clamp((-mv.z - uNear) / ${(2 * R).toFixed(1)}, 0.0, 1.0);
    vLit = (aEnds.x == uFocus || aEnds.y == uFocus) ? 1.0 : 0.0;
    vAlpha = aBase * mix(0.18, 1.0, front) * mix(1.0, 2.4, vLit);
    vT = aT;
    vReach = clamp((uProgress - aDelay) / 0.45, 0.0, 1.0);
  }
`;

const lineFragment = /* glsl */ `
  uniform vec3 uColor;
  uniform vec3 uLit;
  varying float vAlpha;
  varying float vT;
  varying float vReach;
  varying float vLit;

  void main() {
    if (vT > vReach) discard;
    gl_FragColor = vec4(mix(uColor, uLit, vLit), min(vAlpha, 1.0));
    #include <colorspace_fragment>
  }
`;

const pointVertex = /* glsl */ `
  uniform float uProgress;
  uniform float uNear;
  uniform float uScale;
  uniform float uFocus;
  attribute float aRadius;
  attribute float aDelay;
  attribute float aIndex;
  attribute vec3 aColor;
  varying vec3 vColor;
  varying float vAlpha;
  varying float vPx;

  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mv;
    float front = 1.0 - clamp((-mv.z - uNear) / ${(2 * R).toFixed(1)}, 0.0, 1.0);
    float pop = smoothstep(aDelay, aDelay + 0.12, uProgress);
    float focus = aIndex == uFocus ? 1.6 : 1.0;
    vPx = max(aRadius * 2.0 * focus * pop * uScale / -mv.z, 0.0);
    gl_PointSize = vPx + 2.0;
    vColor = aColor;
    vAlpha = mix(0.22, 1.0, front);
  }
`;

const pointFragment = /* glsl */ `
  varying vec3 vColor;
  varying float vAlpha;
  varying float vPx;

  void main() {
    float d = length(gl_PointCoord - 0.5) * (vPx + 2.0);
    float disc = 1.0 - smoothstep(vPx * 0.5 - 1.0, vPx * 0.5, d);
    if (disc < 0.01) discard;
    gl_FragColor = vec4(vColor, disc * vAlpha);
    #include <colorspace_fragment>
  }
`;

function hash(text: string, salt = 0) {
  let h = 2166136261 ^ salt;
  for (let i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 16777619);
  return ((h >>> 0) % 100000) / 100000;
}

function fibonacci(i: number, n: number) {
  const y = 1 - ((i + 0.5) / n) * 2;
  const r = Math.sqrt(1 - y * y);
  const a = i * Math.PI * (3 - Math.sqrt(5));
  return new THREE.Vector3(Math.cos(a) * r, y, Math.sin(a) * r);
}

/** Unit directions for every node: hubs spread evenly, others clustered round a linked hub. */
function arrange(data: GraphData) {
  const dir = new Map<string, THREE.Vector3>();
  const hubs = data.nodes.filter((n) => IS_HUB(n.type));
  hubs.forEach((n, i) => dir.set(n.id, fibonacci(i, Math.max(hubs.length, 1))));
  const linked = new Map<string, string[]>();
  for (const { source, target } of data.links) {
    linked.set(source, [...(linked.get(source) ?? []), target]);
    linked.set(target, [...(linked.get(target) ?? []), source]);
  }
  const rest = data.nodes.filter((n) => !dir.has(n.id));
  // Status-bearing items first so chart types, interfaces and projects can cluster round them in turn.
  rest.sort((a, b) => Number(HAS_STATUS(b.type)) - Number(HAS_STATUS(a.type)));
  rest.forEach((n, i) => {
    const anchor = (linked.get(n.id) ?? []).map((id) => dir.get(id)).find(Boolean);
    if (!anchor) {
      dir.set(n.id, fibonacci(i, rest.length));
      return;
    }
    const tangent = new THREE.Vector3(0, 1, 0).cross(anchor);
    if (tangent.lengthSq() < 1e-6) tangent.set(1, 0, 0);
    tangent.normalize().applyAxisAngle(anchor, hash(n.id) * Math.PI * 2);
    dir.set(n.id, anchor.clone().applyAxisAngle(tangent, 0.2 + hash(n.id, 1) * 0.28));
  });
  return dir;
}

function nodeColor(n: GraphNode) {
  return HAS_STATUS(n.type) && n.status ? STATUS_COLOR[n.status] : TYPE_COLOR[n.type];
}

export class Lattice {
  private renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(32, 1, 1, 2000);
  private model = new THREE.Group();
  private lineMat: THREE.ShaderMaterial;
  private guideMat: THREE.ShaderMaterial;
  private pointMat: THREE.ShaderMaterial;
  private nodes: GraphNode[];
  private positions: THREE.Vector3[];
  private labels: { el: HTMLElement; index: number }[] = [];
  private labelLayer = document.createElement('div');
  private reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  private shared = { uProgress: { value: this.reduced ? 2 : 0 }, uNear: { value: R * 3.1 }, uFocus: { value: -1 } };
  private start = performance.now();
  private spin = 0;
  private velocity = 0.07;
  private drag: { x: number; last: number } | null = null;
  private focus = -1;
  private raf = 0;
  private last = 0;
  private resizeObserver: ResizeObserver;

  constructor(
    private host: HTMLElement,
    data: GraphData,
    private onOpen: (id: string) => void,
    private onHover: (node: GraphNode | null) => void,
  ) {
    this.nodes = data.nodes;
    const dir = arrange(data);
    this.positions = this.nodes.map((n) => dir.get(n.id)!.clone().multiplyScalar(R));

    this.labelLayer.className = 'lattice-labels';
    host.append(this.renderer.domElement, this.labelLayer);
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.camera.position.set(0, 0, R * 4.1);
    this.model.rotation.x = 0.42;
    this.scene.add(this.model);

    // Uniform objects are shared on purpose: one write updates every material.
    const common = this.shared;
    this.lineMat = new THREE.ShaderMaterial({
      vertexShader: lineVertex,
      fragmentShader: lineFragment,
      uniforms: { ...common, uColor: { value: new THREE.Color(INK.ink) }, uLit: { value: new THREE.Color(INK.hub) } },
      transparent: true,
      depthWrite: false,
    });
    this.guideMat = new THREE.ShaderMaterial({
      vertexShader: lineVertex,
      fragmentShader: lineFragment,
      uniforms: { ...common, uFocus: { value: -2 }, uColor: { value: new THREE.Color(INK.indigo) }, uLit: { value: new THREE.Color(INK.indigo) } },
      transparent: true,
      depthWrite: false,
    });
    this.pointMat = new THREE.ShaderMaterial({
      vertexShader: pointVertex,
      fragmentShader: pointFragment,
      uniforms: { ...common, uScale: { value: 1 } },
      transparent: true,
      depthWrite: false,
    });
    this.model.add(this.buildGuides(), this.buildArcs(data), this.buildPoints());
    this.buildLabels();

    this.resizeObserver = new ResizeObserver(this.resize);
    this.resizeObserver.observe(host);
    this.resize();
    this.bindInput();
    this.raf = requestAnimationFrame(this.frame);
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.resizeObserver.disconnect();
    this.model.traverse((o) => (o as THREE.Mesh).geometry?.dispose());
    for (const m of [this.lineMat, this.guideMat, this.pointMat]) m.dispose();
    this.renderer.dispose();
    this.renderer.forceContextLoss(); // the gallery remounts this on every visit
    this.host.replaceChildren();
  }

  /** Armillary rings: equator, three meridians, two latitudes and the polar axis. */
  private buildGuides() {
    const rings: THREE.Vector3[][] = [];
    const circle = (fn: (a: number) => THREE.Vector3) => rings.push(Array.from({ length: 97 }, (_, i) => fn((i / 96) * Math.PI * 2)));
    circle((a) => new THREE.Vector3(Math.cos(a) * R, 0, Math.sin(a) * R));
    for (const m of [0, Math.PI / 3, (2 * Math.PI) / 3]) {
      circle((a) => new THREE.Vector3(Math.cos(a) * R, Math.sin(a) * R, 0).applyAxisAngle(new THREE.Vector3(0, 1, 0), m));
    }
    for (const lat of [-0.6, 0.6]) {
      circle((a) => new THREE.Vector3(Math.cos(a) * R * Math.cos(lat), R * Math.sin(lat), Math.sin(a) * R * Math.cos(lat)));
    }
    rings.push([new THREE.Vector3(0, -R * 1.28, 0), new THREE.Vector3(0, R * 1.28, 0)]);
    return this.segments(rings, rings.map((_, i) => i * 0.04), 0.22, rings.map(() => [-3, -3]));
  }

  private buildArcs(data: GraphData) {
    const index = new Map(this.nodes.map((n, i) => [n.id, i]));
    const arcs: THREE.Vector3[][] = [];
    const ends: [number, number][] = [];
    for (const { source, target } of data.links) {
      const a = index.get(source);
      const b = index.get(target);
      if (a === undefined || b === undefined) continue;
      const u = this.positions[a].clone().normalize();
      const v = this.positions[b].clone().normalize();
      const angle = u.angleTo(v);
      arcs.push(
        Array.from({ length: SEGMENTS + 1 }, (_, s) => {
          const t = s / SEGMENTS;
          // Spherical interpolation, lifted off the surface in the middle.
          const p = angle < 1e-4 ? u.clone() : u.clone().multiplyScalar(Math.sin((1 - t) * angle)).addScaledVector(v, Math.sin(t * angle)).divideScalar(Math.sin(angle));
          return p.normalize().multiplyScalar(R * (1 + 0.14 * Math.sin(Math.PI * t)));
        }),
      );
      ends.push([a, b]);
    }
    return this.segments(arcs, arcs.map((_, i) => 0.25 + (i / Math.max(arcs.length, 1)) * 0.5), 0.26, ends, this.lineMat);
  }

  private segments(polylines: THREE.Vector3[][], delays: number[], base: number, ends: [number, number][], material = this.guideMat) {
    const pos: number[] = [];
    const t: number[] = [];
    const delay: number[] = [];
    const ab: number[] = [];
    polylines.forEach((line, li) => {
      for (let s = 0; s < line.length - 1; s++) {
        pos.push(...line[s].toArray(), ...line[s + 1].toArray());
        t.push(s / (line.length - 1), (s + 1) / (line.length - 1));
        delay.push(delays[li], delays[li]);
        ab.push(...ends[li], ...ends[li]);
      }
    });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute('aT', new THREE.Float32BufferAttribute(t, 1));
    geo.setAttribute('aDelay', new THREE.Float32BufferAttribute(delay, 1));
    geo.setAttribute('aBase', new THREE.Float32BufferAttribute(new Array(t.length).fill(base), 1));
    geo.setAttribute('aEnds', new THREE.Float32BufferAttribute(ab, 2));
    return new THREE.LineSegments(geo, material);
  }

  private buildPoints() {
    const geo = new THREE.BufferGeometry();
    const c = new THREE.Color();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(this.positions.flatMap((p) => p.toArray()), 3));
    geo.setAttribute('aColor', new THREE.Float32BufferAttribute(this.nodes.flatMap((n) => c.set(nodeColor(n)).toArray()), 3));
    geo.setAttribute('aRadius', new THREE.Float32BufferAttribute(this.nodes.map((n) => (IS_HUB(n.type) ? 4.2 : HAS_STATUS(n.type) ? 2.8 : 1.9)), 1));
    geo.setAttribute('aDelay', new THREE.Float32BufferAttribute(this.nodes.map((n, i) => (IS_HUB(n.type) ? 0.05 : 0.2) + (i / this.nodes.length) * 0.5), 1));
    geo.setAttribute('aIndex', new THREE.Float32BufferAttribute(this.nodes.map((_, i) => i), 1));
    return new THREE.Points(geo, this.pointMat);
  }

  private buildLabels() {
    this.nodes.forEach((n, index) => {
      if (!IS_HUB(n.type)) return;
      const el = document.createElement('span');
      el.textContent = n.title;
      this.labelLayer.append(el);
      this.labels.push({ el, index });
    });
  }

  private resize = () => {
    const w = this.host.clientWidth;
    const h = this.host.clientHeight;
    this.renderer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.pointMat.uniforms.uScale.value = (h / 2 / Math.tan(THREE.MathUtils.degToRad(16))) * Math.min(devicePixelRatio, 2);
    this.renderOnce();
  };

  private project(i: number) {
    const world = this.model.localToWorld(this.positions[i].clone());
    const depth = -world.clone().applyMatrix4(this.camera.matrixWorldInverse).z;
    const p = world.project(this.camera);
    return { x: ((p.x + 1) / 2) * this.host.clientWidth, y: ((1 - p.y) / 2) * this.host.clientHeight, front: 1 - Math.min(Math.max((depth - R * 3.1) / (2 * R), 0), 1) };
  }

  private pick(clientX: number, clientY: number) {
    const rect = this.host.getBoundingClientRect();
    let best = -1;
    let bestD = 14;
    this.nodes.forEach((_, i) => {
      const p = this.project(i);
      const d = Math.hypot(p.x - (clientX - rect.left), p.y - (clientY - rect.top)) - p.front * 4;
      if (d < bestD) {
        best = i;
        bestD = d;
      }
    });
    return best;
  }

  private setFocus(i: number) {
    if (i === this.focus) return;
    this.focus = i;
    this.shared.uFocus.value = i;
    this.renderer.domElement.style.cursor = i >= 0 ? 'pointer' : 'grab';
    this.onHover(i >= 0 ? this.nodes[i] : null);
    this.renderOnce();
  }

  private bindInput() {
    const canvas = this.renderer.domElement;
    canvas.style.cursor = 'grab';
    canvas.addEventListener('pointerdown', (e) => {
      this.drag = { x: e.clientX, last: e.clientX };
      canvas.setPointerCapture(e.pointerId);
    });
    canvas.addEventListener('pointermove', (e) => {
      if (this.drag) {
        const dx = e.clientX - this.drag.last;
        this.drag.last = e.clientX;
        this.spin += dx * 0.006;
        this.velocity = dx * 0.35;
        this.renderOnce();
        return;
      }
      this.setFocus(this.pick(e.clientX, e.clientY));
    });
    canvas.addEventListener('pointerup', (e) => {
      const clicked = this.drag && Math.abs(e.clientX - this.drag.x) < 4;
      this.drag = null;
      if (!clicked) return;
      const i = this.pick(e.clientX, e.clientY);
      if (i >= 0) this.onOpen(this.nodes[i].id);
    });
    canvas.addEventListener('pointerleave', () => this.setFocus(-1));
  }

  private renderOnce() {
    this.model.rotation.y = this.spin;
    this.model.updateMatrixWorld();
    this.renderer.render(this.scene, this.camera);
    for (const { el, index } of this.labels) {
      const p = this.project(index);
      el.style.transform = `translate(${p.x}px, ${p.y}px)`;
      el.style.opacity = String(Math.max(p.front * 1.4 - 0.4, 0) * Math.min(this.shared.uProgress.value * 2, 1));
    }
  }

  private frame = (now: number) => {
    this.raf = requestAnimationFrame(this.frame);
    const dt = Math.min((now - (this.last || now)) / 1000, 0.05);
    this.last = now;
    if (this.reduced) return;
    this.shared.uProgress.value = Math.min(((now - this.start) / REVEAL_MS) * 1.4, 2);
    if (!this.drag) {
      // Drag flings decay back to the slow idle turn.
      this.velocity += (0.07 - this.velocity) * Math.min(dt * 1.5, 1);
      this.spin += this.velocity * dt;
    }
    this.renderOnce();
  };
}
