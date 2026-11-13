/*
 * Emphasis per node/link, eased on the CPU each frame:
 * 0 hidden · 0.12 dimmed · 1 normal · 1.3 in focus.
 */

/** Flat journal-figure marks (disc, square or diamond), optionally an inner core with a status ring around it. */
export const nodeVertex = /* glsl */ `
  uniform float uScale;
  attribute vec3 aFill;
  attribute vec3 aRing;
  attribute float aRingOn;
  attribute float aShape;
  attribute float aRadius;
  attribute float aEmph;
  attribute float aBirth;
  varying vec3 vFill;
  varying vec3 vRing;
  varying float vRingOn;
  varying float vShape;
  varying float vAlpha;
  varying float vPx;

  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mv;
    float focus = clamp((aEmph - 1.0) / 0.3, 0.0, 1.0);
    vPx = max(aRadius * 2.0 * (1.0 + 0.4 * focus) * aBirth * uScale / -mv.z, 1.5);
    gl_PointSize = vPx + 2.0;
    vFill = aFill;
    vRing = aRing;
    vRingOn = aRingOn;
    vShape = aShape;
    vAlpha = clamp(aEmph, 0.0, 1.0);
  }
`;

export const nodeFragment = /* glsl */ `
  uniform vec3 uPaper;
  varying vec3 vFill;
  varying vec3 vRing;
  varying float vRingOn;
  varying float vShape;
  varying float vAlpha;
  varying float vPx;

  void main() {
    vec2 p = (gl_PointCoord - 0.5) * (vPx + 2.0);
    // Distance in the mark's own metric, so the ring logic below works for every shape.
    float d = vShape < 0.5 ? length(p) : vShape < 1.5 ? max(abs(p.x), abs(p.y)) * 1.08 : (abs(p.x) + abs(p.y)) * 0.95;
    float r = vPx * 0.5;
    float disc = 1.0 - smoothstep(r - 1.0, r, d);
    if (disc * vAlpha < 0.01) discard;
    vec3 color = vFill;
    if (vRingOn > 0.5) {
      if (vPx < 7.0) {
        color = vRing;
      } else {
        float core = 1.0 - smoothstep(r * 0.55 - 1.0, r * 0.55, d);
        float band = smoothstep(r * 0.72 - 1.0, r * 0.72, d);
        color = mix(mix(uPaper, vRing, band), vFill, core);
      }
    }
    gl_FragColor = vec4(color, disc * vAlpha);
    #include <colorspace_fragment>
  }
`;

export const linkVertex = /* glsl */ `
  attribute vec3 aColor;
  attribute float aAlpha;
  varying vec3 vColor;
  varying float vAlpha;

  void main() {
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    vColor = aColor;
    vAlpha = aAlpha;
  }
`;

export const linkFragment = /* glsl */ `
  varying vec3 vColor;
  varying float vAlpha;

  void main() {
    if (vAlpha < 0.005) discard;
    gl_FragColor = vec4(vColor, vAlpha);
    #include <colorspace_fragment>
  }
`;
