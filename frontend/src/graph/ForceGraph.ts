import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, Simulation } from 'd3-force-3d';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type { GraphData, GraphNode, PageType } from '../api';
import { HAS_STATUS, INK, IS_HUB, STATUS_COLOR, TYPE_COLOR, TYPE_SHAPE } from '../palette';
import { linkFragment, linkVertex, nodeFragment, nodeVertex } from './shaders';

interface Node extends GraphNode {
  x: number;
  y: number;
  z: number;
  vx?: number;
  vy?: number;
  vz?: number;
  fx?: number | null;
  fy?: number | null;
  fz?: number | null;
  r: number;
  degree: number;
}

interface Link {
  source: Node;
  target: Node;
  feeds: boolean;
}

interface Events {
  hover: (id: string | null, x: number, y: number) => void;
  select: (id: string | null) => void;
  open: (id: string) => void;
}

const EMPHASIS = { hidden: 0, dim: 0.12, normal: 1, focus: 1.3 };
const FOV = 40;
const IDLE_ROTATE_MS = 6000;
const FIT_MIN = 280;

function radiusOf(type: PageType, degree: number) {
  if (IS_HUB(type)) return 6 + Math.sqrt(degree) * 1.6;
  if (type === 'layout') return 4 + Math.sqrt(degree) * 0.5;
  if (type === 'template' || type === 'method') return 3.4 + Math.sqrt(degree) * 0.5;
  if (type === 'interface' || type === 'project') return 3.6;
  return 2.6;
}

const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

interface CameraTween {
  fromPos: THREE.Vector3;
  toPos: THREE.Vector3;
  fromTarget: THREE.Vector3;
  toTarget: THREE.Vector3;
  start: number;
  duration: number;
}

/**
 * An Obsidian-style force graph drawn as a journal figure. Flat by default; `setDimensions(3)`
 * lets the layout breathe into depth and enables orbiting. Labels are drawn on a 2D canvas overlay.
 */
export class ForceGraph {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(FOV, 1, 1, 20000);
  private controls: OrbitControls;
  private labels: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private sim: Simulation<Node>;

  private nodes: Node[] = [];
  private links: Link[] = [];
  private byId = new Map<string, Node>();
  private neighbours = new Map<string, Set<string>>();
  private emph = new Float32Array(0);
  private linkEmph = new Float32Array(0);
  private targetCache: { nodes: number[]; links: number[] } = { nodes: [], links: [] };
  private birth = 0;
  private dirty = true;

  private nodeGeo = new THREE.BufferGeometry();
  private linkGeo = new THREE.BufferGeometry();
  private nodeMat: THREE.ShaderMaterial;

  private listeners: { [K in keyof Events]: Set<Events[K]> } = { hover: new Set(), select: new Set(), open: new Set() };
  private hovered: string | null = null;
  private selected: string | null = null;
  private hiddenTypes = new Set<PageType>();
  private showArchived = false;
  private dims: 2 | 3 = 2;
  private flatten: { from: Float32Array; start: number } | null = null;
  private tween: CameraTween | null = null;
  private fitted = { early: false, settled: false };
  private touched = false;
  private dragging: { node: Node; plane: THREE.Plane; moved: boolean; x: number; y: number } | null = null;
  private downAt = { x: 0, y: 0 };
  private lastInput = performance.now();
  private last = 0;
  private raf = 0;
  private reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  private resizeObserver: ResizeObserver;

  constructor(
    private host: HTMLElement,
    data: GraphData,
  ) {
    // Transparent, so the page's flow-field background shows faintly behind the graph.
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.setClearColor(INK.paper, 0);
    this.labels = document.createElement('canvas');
    this.labels.className = 'graph-labels';
    this.ctx = this.labels.getContext('2d')!;
    host.append(this.renderer.domElement, this.labels);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    Object.assign(this.controls, { enableDamping: true, dampingFactor: 0.12, screenSpacePanning: true, zoomToCursor: true, autoRotateSpeed: 0.6 });
    this.applyControlMode();

    this.nodeMat = new THREE.ShaderMaterial({
      vertexShader: nodeVertex,
      fragmentShader: nodeFragment,
      uniforms: { uScale: { value: 1 }, uPaper: { value: new THREE.Color(INK.paper) } },
      transparent: true,
      depthTest: false,
    });
    const linkMat = new THREE.ShaderMaterial({ vertexShader: linkVertex, fragmentShader: linkFragment, transparent: true, depthTest: false });
    this.scene.add(new THREE.LineSegments(this.linkGeo, linkMat), new THREE.Points(this.nodeGeo, this.nodeMat));

    this.sim = forceSimulation<Node>([], 2)
      .velocityDecay(0.32)
      .force('charge', forceManyBody<Node>().strength((n) => -30 - n.degree * 9).distanceMax(600))
      .force('collide', forceCollide<Node>().radius((n) => n.r + 3))
      .force('center', forceCenter<Node>().strength(0.04))
      .stop();

    this.setData(data);
    this.resizeObserver = new ResizeObserver(this.resize);
    this.resizeObserver.observe(host);
    this.resize();
    this.camera.position.set(0, 0, this.homeDistance());
    this.bindInput();
    if (this.reduced) {
      this.sim.tick(300);
      this.birth = 1;
      this.fit(0);
    }
    this.raf = requestAnimationFrame(this.frame);
  }

  // ── public API ───────────────────────────────────────────────

  on<K extends keyof Events>(event: K, fn: Events[K]) {
    this.listeners[event].add(fn);
    return () => void this.listeners[event].delete(fn);
  }

  /** Replace the data, keeping the positions of nodes that already exist. */
  setData(data: GraphData) {
    const old = this.byId;
    const degree = new Map<string, number>();
    for (const l of data.links) for (const id of [l.source, l.target]) degree.set(id, (degree.get(id) ?? 0) + 1);

    this.nodes = data.nodes.map((n) => {
      const prev = old.get(n.id);
      const d = degree.get(n.id) ?? 0;
      // New nodes start near the centre so they bloom outwards.
      const seed = prev ?? { x: (Math.random() - 0.5) * 20, y: (Math.random() - 0.5) * 20, z: 0 };
      return { ...n, x: seed.x, y: seed.y, z: this.dims === 3 ? seed.z : 0, r: radiusOf(n.type, d), degree: d };
    });
    this.byId = new Map(this.nodes.map((n) => [n.id, n]));
    this.links = data.links.flatMap((l) => {
      const source = this.byId.get(l.source);
      const target = this.byId.get(l.target);
      return source && target ? [{ source, target, feeds: l.kind === 'feeds' }] : [];
    });
    this.neighbours = new Map(this.nodes.map((n) => [n.id, new Set<string>()]));
    for (const { source, target } of this.links) {
      this.neighbours.get(source.id)!.add(target.id);
      this.neighbours.get(target.id)!.add(source.id);
    }
    if (this.selected && !this.byId.has(this.selected)) this.selected = null;
    this.hovered = null;

    this.sim.nodes(this.nodes);
    this.sim.force(
      'link',
      forceLink<Node>(this.links)
        .distance((l) => 26 + ((l.source as Node).r + (l.target as Node).r) * 2)
        .strength((l) => 1 / Math.min((l.source as Node).degree, (l.target as Node).degree)),
    );
    this.sim.alpha(old.size ? 0.3 : 1);
    this.buildBuffers();
    this.refreshEmphasis(true);
  }

  setFilter(hiddenTypes: Set<PageType>, showArchived: boolean) {
    this.hiddenTypes = hiddenTypes;
    this.showArchived = showArchived;
    this.refreshEmphasis();
  }

  select(id: string | null) {
    this.selected = id;
    this.refreshEmphasis();
    this.emit('select', id);
    if (!id) return;
    const n = this.byId.get(id)!;
    const target = new THREE.Vector3(n.x, n.y, n.z);
    const offset = this.camera.position.clone().sub(this.controls.target);
    const distance = Math.min(offset.length(), this.homeDistance() * 0.8);
    this.moveCamera(target.clone().add(offset.setLength(distance)), target, 900);
  }

  setDimensions(dims: 2 | 3) {
    if (dims === this.dims) return;
    this.dims = dims;
    this.touched = true;
    this.controls.autoRotate = false;
    const span = Math.max(...this.nodes.map((n) => Math.hypot(n.x, n.y)), 100);
    if (dims === 3) {
      for (const n of this.nodes) {
        n.z = (Math.random() - 0.5) * span * 0.5;
        n.vz = 0;
      }
      this.flatten = null;
      this.sim.numDimensions(3).alpha(0.6);
      const target = this.controls.target.clone();
      const distance = this.camera.position.distanceTo(target);
      this.moveCamera(target.clone().add(new THREE.Vector3(0.55, 0.35, 0.76).setLength(distance)), target, 1400);
    } else {
      this.sim.numDimensions(2).alpha(0.3);
      this.flatten = { from: Float32Array.from(this.nodes, (n) => n.z), start: performance.now() };
      const target = this.controls.target.clone().setZ(0);
      const distance = this.camera.position.distanceTo(this.controls.target);
      this.moveCamera(target.clone().setZ(distance), target, 1200);
    }
    this.applyControlMode();
  }

  get dimensions() {
    return this.dims;
  }

  fit(duration = 900) {
    const visible = this.nodes.filter((n) => this.isVisible(n));
    if (visible.length === 0) return;
    const box = new THREE.Box3().setFromPoints(visible.map((n) => new THREE.Vector3(n.x, n.y, n.z)));
    const centre = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const half = Math.tan(THREE.MathUtils.degToRad(FOV / 2));
    // A small wiki is framed as if it were at least FIT_MIN units across, so a dozen pages read as a constellation, not as giant discs.
    const distance = (Math.max(size.y, size.x / this.camera.aspect, FIT_MIN) / 2 / half) * 1.2 + size.z / 2;
    const direction = this.camera.position.clone().sub(this.controls.target).normalize();
    this.moveCamera(centre.clone().addScaledVector(direction, distance), centre, duration);
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.resizeObserver.disconnect();
    this.sim.stop();
    this.controls.dispose();
    this.nodeGeo.dispose();
    this.linkGeo.dispose();
    this.nodeMat.dispose();
    this.renderer.dispose();
    this.host.replaceChildren();
  }

  // ── internals ────────────────────────────────────────────────

  private emit<K extends keyof Events>(event: K, ...args: Parameters<Events[K]>) {
    for (const fn of this.listeners[event]) (fn as (...a: Parameters<Events[K]>) => void)(...args);
  }

  private isVisible(n: Node) {
    return !this.hiddenTypes.has(n.type) && (this.showArchived || n.status !== 'archived');
  }

  private applyControlMode() {
    const flat = this.dims === 2;
    this.controls.enableRotate = !flat;
    this.controls.mouseButtons = { LEFT: flat ? THREE.MOUSE.PAN : THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
    this.controls.touches = { ONE: flat ? THREE.TOUCH.PAN : THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };
  }

  private homeDistance() {
    return this.host.clientHeight / 2 / Math.tan(THREE.MathUtils.degToRad(FOV / 2));
  }

  private moveCamera(toPos: THREE.Vector3, toTarget: THREE.Vector3, duration: number) {
    this.tween = {
      fromPos: this.camera.position.clone(),
      toPos,
      fromTarget: this.controls.target.clone(),
      toTarget,
      start: performance.now(),
      duration: this.reduced ? 0 : duration,
    };
  }

  private buildBuffers() {
    const n = this.nodes.length;
    const fill = new Float32Array(n * 3);
    const ring = new Float32Array(n * 3);
    const ringOn = new Float32Array(n);
    const shape = Float32Array.from(this.nodes, (x) => TYPE_SHAPE[x.type]);
    const c = new THREE.Color();
    this.nodes.forEach((node, i) => {
      const ringed = HAS_STATUS(node.type);
      const archived = node.status === 'archived';
      c.set(archived ? INK.faint : TYPE_COLOR[node.type]).toArray(fill, i * 3);
      c.set(ringed && node.status ? STATUS_COLOR[node.status] : TYPE_COLOR[node.type]).toArray(ring, i * 3);
      ringOn[i] = ringed && !archived ? 1 : 0;
    });
    this.nodeGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    this.nodeGeo.setAttribute('aFill', new THREE.BufferAttribute(fill, 3));
    this.nodeGeo.setAttribute('aRing', new THREE.BufferAttribute(ring, 3));
    this.nodeGeo.setAttribute('aRingOn', new THREE.BufferAttribute(ringOn, 1));
    this.nodeGeo.setAttribute('aShape', new THREE.BufferAttribute(shape, 1));
    this.nodeGeo.setAttribute('aRadius', new THREE.BufferAttribute(Float32Array.from(this.nodes, (x) => x.r), 1));
    this.nodeGeo.setAttribute('aEmph', new THREE.BufferAttribute(new Float32Array(n), 1));
    this.nodeGeo.setAttribute('aBirth', new THREE.BufferAttribute(new Float32Array(n), 1));
    this.nodeGeo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e6);

    const m = this.links.length;
    this.linkGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(m * 6), 3));
    this.linkGeo.setAttribute('aColor', new THREE.BufferAttribute(new Float32Array(m * 6), 3));
    this.linkGeo.setAttribute('aAlpha', new THREE.BufferAttribute(new Float32Array(m * 2), 1));
    this.linkGeo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e6);

    this.emph = new Float32Array(n);
    this.linkEmph = new Float32Array(m);
  }

  private targets() {
    const focus = this.hovered ?? this.selected;
    const near = focus ? this.neighbours.get(focus)! : null;
    const nodes = this.nodes.map((n) => {
      if (!this.isVisible(n)) return EMPHASIS.hidden;
      if (!focus) return EMPHASIS.normal;
      if (n.id === focus) return EMPHASIS.focus;
      return near!.has(n.id) ? EMPHASIS.normal : EMPHASIS.dim;
    });
    const links = this.links.map(({ source, target }) => {
      if (!this.isVisible(source) || !this.isVisible(target)) return EMPHASIS.hidden;
      if (!focus) return EMPHASIS.normal;
      return source.id === focus || target.id === focus ? EMPHASIS.focus : EMPHASIS.dim;
    });
    return { nodes, links };
  }

  private refreshEmphasis(snap = false) {
    this.targetCache = this.targets();
    if (snap || this.reduced) {
      this.emph.set(this.targetCache.nodes);
      this.linkEmph.set(this.targetCache.links);
    }
  }

  /** Ease emphasis towards its targets; returns true while anything is still moving. */
  private easeEmphasis(dt: number) {
    const k = Math.min(dt * 12, 1);
    let moving = false;
    const step = (cur: Float32Array, goal: number[]) => {
      for (let i = 0; i < cur.length; i++) {
        const d = goal[i] - cur[i];
        if (Math.abs(d) < 0.002) cur[i] = goal[i];
        else {
          cur[i] += d * k;
          moving = true;
        }
      }
    };
    step(this.emph, this.targetCache.nodes);
    step(this.linkEmph, this.targetCache.links);
    return moving;
  }

  private writeBuffers() {
    const pos = this.nodeGeo.getAttribute('position') as THREE.BufferAttribute;
    const p = pos.array as Float32Array;
    this.nodes.forEach((n, i) => {
      p[i * 3] = n.x;
      p[i * 3 + 1] = n.y;
      p[i * 3 + 2] = n.z;
    });
    pos.needsUpdate = true;
    (this.nodeGeo.getAttribute('aEmph').array as Float32Array).set(this.emph);
    this.nodeGeo.getAttribute('aEmph').needsUpdate = true;
    (this.nodeGeo.getAttribute('aBirth').array as Float32Array).fill(this.birth);
    this.nodeGeo.getAttribute('aBirth').needsUpdate = true;

    const lp = this.linkGeo.getAttribute('position').array as Float32Array;
    const lc = this.linkGeo.getAttribute('aColor').array as Float32Array;
    const la = this.linkGeo.getAttribute('aAlpha').array as Float32Array;
    const quiet = new THREE.Color(INK.line);
    const strong = new THREE.Color(INK.ink);
    const flow = new THREE.Color(INK.plum);
    const c = new THREE.Color();
    this.links.forEach(({ source: s, target: t, feeds }, i) => {
      lp.set([s.x, s.y, s.z, t.x, t.y, t.z], i * 6);
      const e = this.linkEmph[i];
      const lit = Math.max(0, (e - 1) / 0.3);
      c.lerpColors(feeds ? flow : quiet, strong, lit).toArray(lc, i * 6);
      c.toArray(lc, i * 6 + 3);
      const alpha = Math.min(e, 1) * ((feeds ? 0.62 : 0.42) + 0.4 * lit) * this.birth;
      la[i * 2] = alpha;
      la[i * 2 + 1] = alpha;
    });
    for (const name of ['position', 'aColor', 'aAlpha']) this.linkGeo.getAttribute(name).needsUpdate = true;
  }

  private resize = () => {
    const w = this.host.clientWidth;
    const h = this.host.clientHeight;
    this.renderer.setSize(w, h);
    const dpr = Math.min(devicePixelRatio, 2);
    this.labels.width = w * dpr;
    this.labels.height = h * dpr;
    this.labels.style.width = `${w}px`;
    this.labels.style.height = `${h}px`;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.nodeMat.uniforms.uScale.value = (h / 2 / Math.tan(THREE.MathUtils.degToRad(FOV / 2))) * dpr;
    this.dirty = true;
  };

  // Screen-space geometry shared by picking and labels.
  private screen(n: Node, v = new THREE.Vector3()) {
    v.set(n.x, n.y, n.z);
    const depth = -v.clone().applyMatrix4(this.camera.matrixWorldInverse).z;
    v.project(this.camera);
    const w = this.host.clientWidth;
    const h = this.host.clientHeight;
    const scale = h / 2 / Math.tan(THREE.MathUtils.degToRad(FOV / 2));
    return { x: ((v.x + 1) / 2) * w, y: ((1 - v.y) / 2) * h, r: (n.r * scale) / depth, behind: depth <= 0 };
  }

  private pick(clientX: number, clientY: number): Node | null {
    const rect = this.host.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    let best: Node | null = null;
    let bestD = Infinity;
    for (const n of this.nodes) {
      if (!this.isVisible(n)) continue;
      const s = this.screen(n);
      if (s.behind) continue;
      const d = Math.hypot(s.x - x, s.y - y);
      if (d < Math.max(s.r, 4) + 4 && d < bestD) {
        best = n;
        bestD = d;
      }
    }
    return best;
  }

  private pointerRay(clientX: number, clientY: number) {
    const rect = this.host.getBoundingClientRect();
    const ndc = new THREE.Vector2(((clientX - rect.left) / rect.width) * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1);
    const ray = new THREE.Raycaster();
    ray.setFromCamera(ndc, this.camera);
    return ray.ray;
  }

  private bindInput() {
    const canvas = this.renderer.domElement;
    const touch = () => {
      this.lastInput = performance.now();
      this.touched = true;
      this.controls.autoRotate = false;
    };
    this.controls.addEventListener('start', () => {
      touch();
      this.tween = null;
    });

    // Capture phase on the host runs before OrbitControls' own pointerdown on the canvas.
    this.host.addEventListener(
      'pointerdown',
      (e) => {
        touch();
        this.downAt = { x: e.clientX, y: e.clientY };
        const node = this.pick(e.clientX, e.clientY);
        if (!node) return;
        this.controls.enabled = false;
        const normal = this.camera.getWorldDirection(new THREE.Vector3());
        this.dragging = { node, plane: new THREE.Plane().setFromNormalAndCoplanarPoint(normal, new THREE.Vector3(node.x, node.y, node.z)), moved: false, x: e.clientX, y: e.clientY };
        canvas.setPointerCapture(e.pointerId);
      },
      { capture: true },
    );

    canvas.addEventListener('pointermove', (e) => {
      if (this.dragging) {
        const d = this.dragging;
        if (!d.moved && Math.hypot(e.clientX - d.x, e.clientY - d.y) < 4) return;
        d.moved = true;
        const hit = this.pointerRay(e.clientX, e.clientY).intersectPlane(d.plane, new THREE.Vector3());
        if (!hit) return;
        d.node.fx = hit.x;
        d.node.fy = hit.y;
        d.node.fz = this.dims === 3 ? hit.z : null;
        this.sim.alphaTarget(0.25).alpha(Math.max(this.sim.alpha(), 0.25));
        return;
      }
      const node = this.pick(e.clientX, e.clientY);
      canvas.style.cursor = node ? 'pointer' : '';
      const id = node?.id ?? null;
      if (id !== this.hovered) {
        this.hovered = id;
        this.refreshEmphasis();
      }
      this.emit('hover', id, e.clientX, e.clientY);
    });

    const release = (e: PointerEvent) => {
      const d = this.dragging;
      if (!d) return;
      this.dragging = null;
      this.controls.enabled = true;
      d.node.fx = d.node.fy = d.node.fz = null;
      this.sim.alphaTarget(0);
      if (canvas.hasPointerCapture(e.pointerId)) canvas.releasePointerCapture(e.pointerId);
      if (!d.moved) this.select(d.node.id === this.selected ? null : d.node.id);
    };
    canvas.addEventListener('pointerup', release);
    canvas.addEventListener('pointercancel', release);

    canvas.addEventListener('pointerleave', () => {
      if (this.dragging) return;
      this.hovered = null;
      this.refreshEmphasis();
      this.emit('hover', null, 0, 0);
    });
    // A plain click on empty paper clears the selection; node clicks are handled in release().
    canvas.addEventListener('click', (e) => {
      const still = Math.hypot(e.clientX - this.downAt.x, e.clientY - this.downAt.y) < 4;
      if (still && this.selected && !this.pick(e.clientX, e.clientY)) this.select(null);
    });
    canvas.addEventListener('dblclick', (e) => {
      const node = this.pick(e.clientX, e.clientY);
      if (node) this.emit('open', node.id);
    });
    canvas.addEventListener('wheel', touch, { passive: true });
  }

  private drawLabels() {
    const ctx = this.ctx;
    const w = this.host.clientWidth;
    const h = this.host.clientHeight;
    ctx.clearRect(0, 0, w, h);
    const focus = this.hovered ?? this.selected;
    const near = focus ? this.neighbours.get(focus)! : null;
    const v = new THREE.Vector3();
    this.drawArrows();

    const candidates = this.nodes.flatMap((n, i) => {
      const e = this.emph[i];
      if (e < 0.05) return [];
      const s = this.screen(n, v);
      if (s.behind || s.x < -100 || s.x > w + 100 || s.y < -40 || s.y > h + 40) return [];
      const important = n.id === focus || !!near?.has(n.id);
      const hub = IS_HUB(n.type);
      // Ordinary labels fade in as you zoom in, like a map.
      const zoomAlpha = Math.min(Math.max((s.r - 3) / 2.5, 0), 1);
      const alpha = (important || hub ? 1 : zoomAlpha) * Math.min(e, 1) * this.birth;
      if (alpha < 0.03) return [];
      return [{ n, s, alpha, priority: n.id === focus ? 3 : important ? 2 : hub ? 1.5 : 1 }];
    });
    candidates.sort((a, b) => b.priority - a.priority || b.n.degree - a.n.degree);

    const taken: { x0: number; x1: number; y0: number; y1: number }[] = [];
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.lineJoin = 'round';
    for (const { n, s, alpha, priority } of candidates) {
      const hub = IS_HUB(n.type);
      ctx.font = hub ? `600 ${priority >= 2 ? 14 : 13}px "Noto Serif SC", serif` : `${priority >= 2 ? 12 : 11}px "Archivo Variable", "Microsoft YaHei", sans-serif`;
      const text = priority >= 2 || n.title.length <= 16 ? n.title : `${n.title.slice(0, 15)}…`;
      const width = ctx.measureText(text).width;
      const top = s.y + Math.max(s.r, 2) + 4;
      const box = { x0: s.x - width / 2 - 2, x1: s.x + width / 2 + 2, y0: top - 1, y1: top + 15 };
      if (priority < 2 && taken.some((t) => box.x0 < t.x1 && box.x1 > t.x0 && box.y0 < t.y1 && box.y1 > t.y0)) continue;
      taken.push(box);
      ctx.globalAlpha = alpha;
      ctx.lineWidth = 4;
      ctx.strokeStyle = INK.paper;
      ctx.strokeText(text, s.x, top);
      ctx.fillStyle = hub ? INK.hub : priority >= 2 ? INK.ink : INK.muted;
      ctx.fillText(text, s.x, top);
    }
    ctx.globalAlpha = 1;
  }

  /** Arrowheads for analysis-to-figure links, drawn in screen space so they keep their size at any zoom. */
  private drawArrows() {
    const ctx = this.ctx;
    const a = new THREE.Vector3();
    const b = new THREE.Vector3();
    this.links.forEach(({ source, target, feeds }, i) => {
      const e = this.linkEmph[i];
      if (!feeds || e < 0.05) return;
      const s = this.screen(source, a);
      const t = this.screen(target, b);
      if (s.behind || t.behind) return;
      const dx = t.x - s.x;
      const dy = t.y - s.y;
      const len = Math.hypot(dx, dy);
      if (len < t.r + 12) return;
      const ux = dx / len;
      const uy = dy / len;
      const tipX = t.x - ux * (t.r + 2);
      const tipY = t.y - uy * (t.r + 2);
      const size = 7;
      ctx.globalAlpha = Math.min(e, 1) * this.birth;
      ctx.fillStyle = e > 1.05 ? INK.ink : INK.plum;
      ctx.beginPath();
      ctx.moveTo(tipX, tipY);
      ctx.lineTo(tipX - ux * size - uy * size * 0.5, tipY - uy * size + ux * size * 0.5);
      ctx.lineTo(tipX - ux * size + uy * size * 0.5, tipY - uy * size - ux * size * 0.5);
      ctx.fill();
    });
    ctx.globalAlpha = 1;
  }

  private stepCamera(now: number) {
    const t = this.tween!;
    const k = t.duration === 0 ? 1 : Math.min((now - t.start) / t.duration, 1);
    const e = easeInOut(k);
    this.camera.position.lerpVectors(t.fromPos, t.toPos, e);
    this.controls.target.lerpVectors(t.fromTarget, t.toTarget, e);
    if (k === 1) this.tween = null;
  }

  private stepFlatten(now: number) {
    const f = this.flatten!;
    const k = this.reduced ? 1 : Math.min((now - f.start) / 900, 1);
    const e = easeInOut(k);
    this.nodes.forEach((n, i) => {
      n.z = f.from[i] * (1 - e);
      n.vz = 0;
    });
    if (k === 1) this.flatten = null;
  }

  private frame = (now: number) => {
    this.raf = requestAnimationFrame(this.frame);
    const dt = Math.min((now - (this.last || now)) / 1000, 0.05);
    this.last = now;

    const simming = this.sim.alpha() > 0.002;
    // Advance by elapsed time, so the layout settles at the same pace on a slow frame rate.
    if (simming) this.sim.tick(Math.min(Math.max(Math.round(dt * 60), 1), 4));
    if (this.flatten) this.stepFlatten(now);
    if (this.birth < 1) this.birth = Math.min(this.birth + dt / 0.6, 1);

    if (!this.touched && !this.fitted.early && this.sim.alpha() < 0.35) {
      this.fitted.early = true;
      this.fit(1100);
    }
    if (!this.touched && !this.fitted.settled && this.sim.alpha() < 0.02) {
      this.fitted.settled = true;
      this.fit(800);
    }

    if (this.tween) this.stepCamera(now);
    if (this.dims === 3 && !this.reduced && !this.dragging && now - this.lastInput > IDLE_ROTATE_MS) this.controls.autoRotate = true;
    const cameraMoved = this.controls.update() || !!this.tween;
    const emphMoving = this.easeEmphasis(dt);

    if (!(simming || this.flatten || cameraMoved || emphMoving || this.birth < 1 || this.controls.autoRotate || this.dirty)) return;
    this.dirty = false;
    this.writeBuffers();
    this.renderer.render(this.scene, this.camera);
    this.drawLabels();
  };
}
