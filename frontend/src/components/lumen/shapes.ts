/**
 * Target shapes for the Lumen's particles.
 *
 * Every shape is generated from code with a seeded random source, so the server and
 * the browser produce the same dots (no hydration mismatch) and no image asset is
 * needed. Coordinates are in a square from -1 to 1 with y pointing down; the third
 * value of each point is a weight from 0 to 1 that becomes dot size and brightness.
 */
export type LumenMode = "orb" | "figure" | "pair" | "week";

export const MAX_PARTICLES = 840;
export const DAYS = 7;

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** A soft disc: even spacing (golden-angle spiral), brighter toward the middle. */
function orb(count: number): Float32Array {
  const points = new Float32Array(count * 3);
  for (let i = 0; i < count; i += 1) {
    const radius = Math.sqrt((i + 0.5) / count) * 0.8;
    const angle = i * 2.399963229728653;
    points[i * 3] = Math.cos(angle) * radius;
    points[i * 3 + 1] = Math.sin(angle) * radius;
    points[i * 3 + 2] = 1 - (radius / 0.8) * 0.78;
  }
  return points;
}

type Field = (x: number, y: number) => number;

/** Fill a shape described by a weight function (0 means outside). */
function sample(count: number, field: Field, seed: number): Float32Array {
  const random = mulberry32(seed);
  const points = new Float32Array(count * 3);
  let placed = 0;
  let guard = 0;
  while (placed < count && guard < count * 400) {
    guard += 1;
    const x = random() * 2 - 1;
    const y = random() * 2 - 1;
    const weight = field(x, y);
    if (weight <= 0) continue;
    points[placed * 3] = x;
    points[placed * 3 + 1] = y;
    points[placed * 3 + 2] = weight;
    placed += 1;
  }
  return points;
}

function disc(x: number, y: number, cx: number, cy: number, r: number): number {
  const d = Math.hypot(x - cx, y - cy) / r;
  return d < 1 ? 1 - d * 0.6 : 0;
}

/** Distance from a point to a line segment, for arms. */
function capsule(
  x: number,
  y: number,
  ax: number,
  ay: number,
  bx: number,
  by: number,
  r: number,
): number {
  const dx = bx - ax;
  const dy = by - ay;
  const t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)));
  const d = Math.hypot(x - (ax + dx * t), y - (ay + dy * t)) / r;
  return d < 1 ? 0.75 - d * 0.35 : 0;
}

/** A seated, faceless figure: a head and rounded shoulders that fade downward. */
function figure(x: number, y: number, cx: number, scale: number): number {
  const head = disc(x, y, cx, -0.5 * scale, 0.17 * scale);
  if (head > 0) return 0.55 + head * 0.45;
  const bx = (x - cx) / (0.34 * scale);
  const by = (y - 0.26 * scale) / (0.56 * scale);
  if (y < -0.28 * scale || bx * bx + by * by >= 1) return 0;
  // Brighter at the shoulders, dimmer toward the base, like light falling from above.
  return Math.max(0.3, 0.9 - (y + 0.28 * scale) / (1.3 * scale));
}

function pair(x: number, y: number): number {
  const light = disc(x, y, 0, -0.16, 0.085);
  if (light > 0) return 1;
  const left = figure(x, y, -0.47, 0.78);
  const right = figure(x, y, 0.47, 0.78);
  const leftArm = capsule(x, y, -0.3, -0.08, -0.08, -0.16, 0.045);
  const rightArm = capsule(x, y, 0.3, -0.08, 0.08, -0.16, 0.045);
  return Math.max(left, right, leftArm, rightArm);
}

/** Seven small clusters in a shallow arc, one per day. Lit days are bright. */
function week(count: number, lit: readonly boolean[]): Float32Array {
  const random = mulberry32(77);
  const points = new Float32Array(count * 3);
  for (let i = 0; i < count; i += 1) {
    const day = i % DAYS;
    const cx = -0.78 + day * 0.26;
    const cy = 0.1 * Math.cos((day - 3) * 0.5) - 0.06;
    const radius = Math.sqrt(random()) * 0.098;
    const angle = random() * Math.PI * 2;
    points[i * 3] = cx + Math.cos(angle) * radius;
    points[i * 3 + 1] = cy + Math.sin(angle) * radius;
    points[i * 3 + 2] = lit[day] ? 1 - (radius / 0.098) * 0.5 : 0.16;
  }
  return points;
}

const cache = new Map<string, Float32Array>();

/**
 * Points for a shape. `count` defaults to the animated particle count; the static
 * image asks for fewer and gets its own evenly spread set rather than a subsample.
 */
export function targets(
  mode: LumenMode,
  lit: readonly boolean[] = [],
  count: number = MAX_PARTICLES,
): Float32Array {
  const litKey = mode === "week" ? lit.map((v) => (v ? 1 : 0)).join("") : "";
  const key = `${mode}:${litKey}:${count}`;
  const existing = cache.get(key);
  if (existing) return existing;
  let points: Float32Array;
  if (mode === "orb") points = orb(count);
  else if (mode === "figure") points = sample(count, (x, y) => figure(x, y, 0, 1), 11);
  else if (mode === "pair") points = sample(count, pair, 29);
  else points = week(count, lit);
  cache.set(key, points);
  return points;
}

/** Color of the light for a hue setting from 0 (cool violet) to 1 (soft teal). */
export function lumenColor(hue: number, light: boolean): [number, number, number] {
  const h = 262 - Math.max(0, Math.min(1, hue)) * 92;
  return [h, light ? 62 : 84, light ? 38 : 76];
}
