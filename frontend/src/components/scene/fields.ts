/**
 * Brightness fields for the dithered scenes (docs/design-plan.md, "Scenes").
 *
 * A scene is a function from a point to a brightness. The renderer turns brightness
 * into dots with an ordered dither, which is what gives the halftone look. Everything
 * is computed from code: there is no photograph, no model and no image of a person.
 *
 * Coordinates: y runs from -1 (top) to 1 (bottom); x runs from -aspect to aspect.
 * This file has no imports and no DOM access, so the same code runs in the browser
 * (animated canvas) and in Node (scripts/make-scenes.mjs, which writes the stills).
 */
export type SceneName = "held" | "point" | "figure" | "pair" | "terrain";

export const SCENES: readonly SceneName[] = ["held", "point", "figure", "pair", "terrain"];

/** Brightness is quantised to this many tones. */
export const TONES = 6;

/** Dot colors from faintest to brightest, as RGB. */
export const PALETTE: Record<"night" | "daybreak", readonly (readonly [number, number, number])[]> = {
  night: [
    [47, 43, 138],
    [77, 71, 201],
    [111, 105, 234],
    [147, 141, 255],
    [196, 192, 255],
    [255, 255, 255],
  ],
  daybreak: [
    [176, 172, 232],
    [143, 137, 220],
    [106, 99, 207],
    [74, 65, 201],
    [47, 40, 150],
    [20, 21, 42],
  ],
};

const BAYER = [
  0, 32, 8, 40, 2, 34, 10, 42, 48, 16, 56, 24, 50, 18, 58, 26, 12, 44, 4, 36, 14, 46, 6, 38, 60,
  28, 52, 20, 62, 30, 54, 22, 3, 35, 11, 43, 1, 33, 9, 41, 51, 19, 59, 27, 49, 17, 57, 25, 15, 47,
  7, 39, 13, 45, 5, 37, 63, 31, 55, 23, 61, 29, 53, 21,
];

/** A repeatable pseudo-random number in [0, 1) for a cell. */
export function hash(i: number, j: number, salt = 0): number {
  let h = (Math.imul(i, 374761393) + Math.imul(j, 668265263) + Math.imul(salt, 2147483647)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

/**
 * The dither threshold for a cell: mostly the regular Bayer pattern, partly noise so
 * large areas do not look mechanical. `drift` slides the noisy part, which is the
 * whole of the shimmer animation.
 */
export function threshold(i: number, j: number, drift = 0): number {
  const ordered = (BAYER[(j & 7) * 8 + (i & 7)]! + 0.5) / 64;
  const noise = (hash(i, j) + drift) % 1;
  return ordered * 0.6 + noise * 0.4;
}

/** True for the few cells that are background stars. */
export function isStar(i: number, j: number): boolean {
  return hash(i, j, 7) < 0.0028;
}

const exp = Math.exp;
const hypot = Math.hypot;

function capsule(x: number, y: number, ax: number, ay: number, bx: number, by: number, r: number) {
  const dx = bx - ax;
  const dy = by - ay;
  const t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)));
  return hypot(x - (ax + dx * t), y - (ay + dy * t)) - r;
}

/** Signed distance to a standing, faceless figure. (cx, cy) is the hip; s is the size. */
function person(x: number, y: number, cx: number, cy: number, s: number): number {
  const px = Math.abs(x - cx);
  const py = y - cy;
  const head = hypot(px, py + 0.8 * s) - 0.095 * s;
  const torso = capsule(px, py, 0, -0.56 * s, 0, -0.14 * s, 0.115 * s);
  const arm = capsule(px, py, 0.15 * s, -0.58 * s, 0.3 * s, 0.0, 0.034 * s);
  const leg = capsule(px, py, 0.06 * s, -0.08 * s, 0.085 * s, 0.78 * s, 0.052 * s);
  return Math.min(head, torso, arm, leg);
}

// Each scene writes two numbers: light that stays still, and light that breathes.
let still = 0;
let glow = 0;

function held(x: number, y: number, a: number): void {
  const wide = a > 1;
  const ox = wide ? a * 0.06 : -0.04;
  const oy = wide ? -0.4 : -0.46;
  const k = wide ? 0.8 : 0.6;
  const dx = (x - ox) / k;
  const dy = (y - oy) / k;
  const d = hypot(dx, dy);
  const angle = Math.atan2(dy, dx);

  // A round body of light, brightest in the middle, with a soft edge.
  const radius = 0.21;
  const inside = d < radius ? 0.42 + 0.8 * (1 - (d / radius) ** 2) : 0;
  const core = inside + (d > radius ? 0.4 * exp(-(d - radius) / 0.05) : 0);
  const halo = 0.4 * exp(-d / 0.3);
  // Rays begin at the edge of the light, so the middle stays round.
  const outside = d > radius ? 1 : 0;
  const ray = (at: number, sharp: number, reach: number, power: number) =>
    power * outside * Math.max(0, Math.cos(angle - at)) ** sharp * exp(-d / reach);
  const rays =
    ray(-0.82, 700, 0.6, 2.4) + ray(-2.3, 600, 0.42, 2.2) + ray(2.75, 500, 0.36, 1.8) + ray(0.5, 900, 0.2, 1.6);
  // The dark band across the light, as if something is cupped around it.
  const shade = 1.25 * exp(-(((dx - 0.02) / 0.17) ** 2 + ((dy - 0.07) / 0.05) ** 2));

  // An open hand rising from the lower right: flat tone, like a paper cut-out.
  const palm = hypot((dx - 0.5) / 0.17, (dy - 0.22) / 0.2) - 1;
  const wrist = capsule(dx, dy, 0.54, 0.34, 0.8, 1.0, 0.115);
  const thumb = capsule(dx, dy, 0.38, 0.24, 0.2, 0.1, 0.045);
  const digits = Math.min(
    capsule(dx, dy, 0.4, 0.08, 0.31, -0.2, 0.038),
    capsule(dx, dy, 0.48, 0.05, 0.43, -0.3, 0.04),
    capsule(dx, dy, 0.56, 0.06, 0.56, -0.27, 0.038),
    capsule(dx, dy, 0.63, 0.1, 0.67, -0.16, 0.034),
  );
  let hand = 0;
  if (palm < 0 || wrist < 0 || thumb < 0 || digits < 0) {
    hand = 0.34 + 0.4 * exp(-d / 0.3) - Math.max(0, dy - 0.3) * 0.28;
  }
  // Fingers of the other hand curling under the light from the left.
  const under = d > 0.25 && d < 0.35 && angle > 1.2 && angle < 3.0;
  const fingers = under ? 0.3 * (0.55 + 0.45 * Math.sin(angle * 10)) : 0;

  still = Math.max(halo, hand, fingers) - shade * 0.2 + 0.1 * exp(-d / 0.9);
  glow = (core + rays) * (1 - Math.min(0.62, shade * 0.6));
}

function point(x: number, y: number): void {
  const d = hypot(x, y);
  let rings = 0;
  for (const radius of [0.34, 0.58, 0.82]) rings += 0.42 * exp(-(((d - radius) / 0.013) ** 2));
  still = rings + 0.3 * exp(-d / 0.22);
  glow = 1.4 * exp(-((d / 0.055) ** 2)) + 0.5 * exp(-d / 0.09);
}

function figure(x: number, y: number): void {
  const d = person(x, y, 0, 0.08, 0.9);
  const centre = hypot(x, y + 0.2);
  let rings = 0;
  for (const radius of [0.5, 0.66, 0.84]) rings += 0.42 * exp(-(((centre - radius) / 0.013) ** 2));
  // Brightest at the head and chest; the legs dissolve into the dark.
  const fade = Math.max(0.12, Math.min(1, 0.95 - (y + 0.05) * 1.05));
  const depth = Math.min(1, Math.max(0, -d) / 0.05);
  still = rings + (d < 0 ? (0.3 + 0.2 * depth) * fade : 0);
  glow = (d < 0 ? 0.45 * depth * fade : 0) + 0.85 * exp(-Math.max(0, d) / 0.075) * fade;
}

function ridges(x: number, y: number): number {
  let total = 0;
  for (let n = 0; n < 5; n += 1) {
    const line =
      -0.02 + n * 0.21 + (0.1 - n * 0.012) * Math.sin(x * (1.3 + n * 0.37) + n * 1.9) +
      0.035 * Math.sin(x * (3.9 + n) + n * 0.7);
    const below = y - line;
    const strength = 0.62 - n * 0.07;
    total += strength * (below < 0 ? exp(below / 0.012) : exp(-below / (0.09 + n * 0.02)));
  }
  return Math.min(0.85, total);
}

function terrain(x: number, y: number): void {
  still = ridges(x, y) * Math.max(0, Math.min(1, 1.15 - Math.abs(x) * 0.22));
  glow = 0;
}

function pair(x: number, y: number): void {
  terrain(x, y);
  const size = 0.4;
  const ground = 0.02;
  const left = person(x, y, -0.2, ground - 0.3, size);
  const right = person(x, y, 0.2, ground - 0.3, size);
  const hands = capsule(x, y, -0.09, ground - 0.5, 0.09, ground - 0.5, 0.014);
  const lit = Math.min(right, hands);
  if (left < 0) still = Math.max(still, 0.42);
  glow = (lit < 0 ? 1 : 0) + 0.45 * exp(-Math.max(0, lit) / 0.05);
}

export type Sample = { still: number; glow: number };
const out: Sample = { still: 0, glow: 0 };

/** Brightness at a point. The returned object is reused between calls. */
export function sample(scene: SceneName, x: number, y: number, aspect: number): Sample {
  if (scene === "held") held(x, y, aspect);
  else if (scene === "point") point(x, y);
  else if (scene === "figure") figure(x, y);
  else if (scene === "pair") pair(x, y);
  else terrain(x, y);
  out.still = still;
  out.glow = glow;
  return out;
}

/** Tone index for a brightness, or -1 when the cell stays empty. */
export function tone(brightness: number, i: number, j: number, drift = 0): number {
  if (brightness > threshold(i, j, drift)) {
    return Math.min(TONES - 1, Math.floor(Math.min(1, brightness) * (TONES - 0.01)));
  }
  return isStar(i, j) ? 1 : -1;
}
