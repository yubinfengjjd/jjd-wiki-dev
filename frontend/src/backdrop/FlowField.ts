import { INK } from '../palette';
import { createNoise2D } from './noise';

/*
 * The page background: thousands of short ink strokes drifting along a slowly
 * changing flow field, like a vector-field plot in a physics text. The pointer
 * parts the streamlines. A few strokes are green. Intensity is set per page zone.
 */

const TRAIL = 20;
const SCALE = 0.0017;
const SPEED = 42; // px per second
const PUSH_RADIUS = 170;
const ALPHA = 0.32;
const BUCKETS = 4;

export class FlowField {
  private ctx: CanvasRenderingContext2D;
  private noise = createNoise2D(17);
  private count = 0;
  private trail = new Float32Array(0); // count × TRAIL × 2, newest point first
  private life = new Float32Array(0);
  private span = new Float32Array(0);
  private green = new Uint8Array(0);
  private pointer = { x: -1e4, y: -1e4 };
  private time = 0;
  private last = 0;
  private reduced = matchMedia('(prefers-reduced-motion: reduce)');

  constructor(private canvas: HTMLCanvasElement) {
    this.ctx = canvas.getContext('2d')!;
    this.resize();
    addEventListener('resize', this.resize);
    addEventListener('pointermove', (e) => (this.pointer = { x: e.clientX, y: e.clientY }), { passive: true });
    document.documentElement.addEventListener('pointerleave', () => (this.pointer = { x: -1e4, y: -1e4 }));
    this.reduced.addEventListener('change', () => this.draw());
    requestAnimationFrame(this.frame);
  }

  /** 0–1; eased by a CSS transition on the canvas. */
  setIntensity(value: number) {
    this.canvas.style.opacity = String(value);
  }

  private resize = () => {
    const dpr = Math.min(devicePixelRatio, 1.5);
    const w = innerWidth;
    const h = innerHeight;
    this.canvas.width = w * dpr;
    this.canvas.height = h * dpr;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.count = Math.min(Math.round((w * h) / 950), 2400);
    this.trail = new Float32Array(this.count * TRAIL * 2);
    this.life = new Float32Array(this.count);
    this.span = new Float32Array(this.count);
    this.green = new Uint8Array(this.count);
    for (let i = 0; i < this.count; i++) this.spawn(i, Math.random());
    // Let the strokes grow their tails before the first paint.
    for (let k = 0; k < TRAIL; k++) this.step(1 / 30);
    this.draw();
  };

  /** Place particle i at a random point; `age` (0–1) staggers lifetimes so they do not blink in unison. */
  private spawn(i: number, age = 0) {
    const x = Math.random() * innerWidth;
    const y = Math.random() * innerHeight;
    const base = i * TRAIL * 2;
    for (let k = 0; k < TRAIL; k++) {
      this.trail[base + k * 2] = x;
      this.trail[base + k * 2 + 1] = y;
    }
    this.span[i] = 5 + Math.random() * 7;
    this.life[i] = age * this.span[i];
    this.green[i] = Math.random() < 0.05 ? 1 : 0;
  }

  private angle(x: number, y: number) {
    const t = this.time;
    const n = this.noise(x * SCALE + t * 0.02, y * SCALE) + 0.5 * this.noise(x * SCALE * 2.3, y * SCALE * 2.3 - t * 0.035);
    return n * Math.PI * 1.4;
  }

  private step(dt: number) {
    this.time += dt;
    const { x: px, y: py } = this.pointer;
    const w = innerWidth;
    const h = innerHeight;
    for (let i = 0; i < this.count; i++) {
      this.life[i] += dt;
      const base = i * TRAIL * 2;
      let x = this.trail[base];
      let y = this.trail[base + 1];
      if (this.life[i] > this.span[i] || x < -20 || x > w + 20 || y < -20 || y > h + 20) {
        this.spawn(i);
        continue;
      }
      const a = this.angle(x, y);
      let vx = Math.cos(a);
      let vy = Math.sin(a);
      const dx = x - px;
      const dy = y - py;
      const d = Math.hypot(dx, dy);
      if (d < PUSH_RADIUS && d > 0.1) {
        // Push outwards and swirl a little, like a finger drawn through the plot.
        const f = (1 - d / PUSH_RADIUS) ** 2 * 2.6;
        vx += ((dx - dy * 0.6) / d) * f;
        vy += ((dy + dx * 0.6) / d) * f;
      }
      x += vx * SPEED * dt;
      y += vy * SPEED * dt;
      this.trail.copyWithin(base + 2, base, base + (TRAIL - 1) * 2);
      this.trail[base] = x;
      this.trail[base + 1] = y;
    }
  }

  private draw() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, innerWidth, innerHeight);
    ctx.lineWidth = 1.1;
    ctx.lineCap = 'round';
    // Strokes fade in and out over their life; batching by fade bucket keeps this to a few paths.
    for (const green of [0, 1]) {
      for (let b = 1; b <= BUCKETS; b++) {
        ctx.beginPath();
        for (let i = 0; i < this.count; i++) {
          if (this.green[i] !== green) continue;
          const fade = Math.min(this.life[i] / 1.2, (this.span[i] - this.life[i]) / 1.2, 1);
          if (Math.ceil(fade * BUCKETS) !== b) continue;
          const base = i * TRAIL * 2;
          ctx.moveTo(this.trail[base], this.trail[base + 1]);
          for (let k = 1; k < TRAIL; k++) ctx.lineTo(this.trail[base + k * 2], this.trail[base + k * 2 + 1]);
        }
        ctx.strokeStyle = green ? INK.hub : INK.ink;
        ctx.globalAlpha = (ALPHA * (green ? 1.8 : 1) * b) / BUCKETS;
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
  }

  private frame = (now: number) => {
    requestAnimationFrame(this.frame);
    const dt = Math.min((now - (this.last || now)) / 1000, 0.05);
    this.last = now;
    if (this.reduced.matches) return;
    this.step(dt);
    this.draw();
  };
}
