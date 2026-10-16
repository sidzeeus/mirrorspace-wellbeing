"use client";

/**
 * The Lumen: the app's one glowing object. See docs/lumen.md.
 *
 * It is never decoration. Every use passes a `label` that says what the light is
 * showing, and the props map to something real (a mood value, a breath, a week).
 *
 * Rendering chain:
 *   1. A static SVG of dots, rendered on the server. Always present, works without
 *      JavaScript, and is what reduced-motion and low-bandwidth users keep.
 *   2. WebGL points, when the browser allows animation.
 *   3. Canvas 2D, if WebGL is unavailable.
 * It measures its own frame rate: below 50 fps it halves its particles, and if that
 * is not enough it stops and shows the static image again.
 */
import { useEffect, useMemo, useRef, useState } from "react";

import { useLowBandwidth, useReducedMotion } from "@/lib/prefs";

import { type LumenMode, MAX_PARTICLES, lumenColor, targets } from "./shapes";

export type LumenProps = {
  /** What the light is showing, for screen readers and as the image's name. */
  label: string;
  mode?: LumenMode;
  /** Brightness, 0 to 1. */
  intensity?: number;
  /** Share of particles shown, 0 to 1. */
  density?: number;
  /** 0 is cool violet, 1 is soft teal. */
  hue?: number;
  /** Breath, 0 (fully out) to 1 (fully in). Leave undefined when not breathing. */
  breathPhase?: number;
  /** For mode "week": which of the seven days are lit. */
  lit?: readonly boolean[];
  /** Gather from scattered points on first appearance. */
  assemble?: boolean;
  /** Restlessness of the points, 0 (calm) to 1 (a storm). */
  agitation?: number;
  /** Vertical shift: positive sinks the shape, negative lifts it. About -1 to 1. */
  lift?: number;
  /** How far the points scatter from the shape, 0 to 1. */
  spread?: number;
  className?: string;
};

const STATIC_DOTS = 260;
const MIN_PARTICLES = 210;
const LEVELS = 4;

type Renderer = "static" | "webgl" | "canvas2d";
type Live = Required<
  Pick<LumenProps, "mode" | "intensity" | "density" | "hue" | "agitation" | "lift" | "spread">
> & {
  breathPhase: number | undefined;
  lit: readonly boolean[];
};

const clamp01 = (value: number) => Math.max(0, Math.min(1, value));
const breathScale = (phase: number | undefined) =>
  phase === undefined ? 1 : 0.72 + 0.28 * clamp01(phase);

/** Ordered-dither style quantisation: weights snap to a few levels, like halftone. */
function level(weight: number, intensity: number, index: number): number {
  const jitter = (((index * 7919) % 97) / 97 - 0.5) * 0.22;
  const value = clamp01(weight * (0.3 + 0.7 * intensity) + jitter);
  return Math.ceil(value * LEVELS) / LEVELS;
}

const VERTEX = `attribute vec2 p;attribute float s;attribute float a;varying float v;
void main(){v=a;gl_Position=vec4(p.x,-p.y,0.,1.);gl_PointSize=s;}`;
const FRAGMENT = `precision mediump float;uniform vec3 c;varying float v;
void main(){float d=length(gl_PointCoord-.5);float m=smoothstep(.5,.34,d);gl_FragColor=vec4(c*v*m,v*m);}`;

function hslToRgb(h: number, s: number, l: number): [number, number, number] {
  const sat = s / 100;
  const light = l / 100;
  const k = (n: number) => (n + h / 30) % 12;
  const a = sat * Math.min(light, 1 - light);
  const f = (n: number) => light - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  return [f(0), f(8), f(4)];
}

function createGl(canvas: HTMLCanvasElement) {
  const gl = canvas.getContext("webgl", { alpha: true, antialias: false, premultipliedAlpha: true });
  if (!gl) return null;
  const compile = (type: number, source: string) => {
    const shader = gl.createShader(type);
    if (!shader) return null;
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    return gl.getShaderParameter(shader, gl.COMPILE_STATUS) ? shader : null;
  };
  const vertex = compile(gl.VERTEX_SHADER, VERTEX);
  const fragment = compile(gl.FRAGMENT_SHADER, FRAGMENT);
  const program = gl.createProgram();
  if (!vertex || !fragment || !program) return null;
  gl.attachShader(program, vertex);
  gl.attachShader(program, fragment);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return null;
  gl.useProgram(program);
  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  const stride = 16;
  for (const [name, size, offset] of [["p", 2, 0], ["s", 1, 8], ["a", 1, 12]] as const) {
    const location = gl.getAttribLocation(program, name);
    gl.enableVertexAttribArray(location);
    gl.vertexAttribPointer(location, size, gl.FLOAT, false, stride, offset);
  }
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
  return { gl, color: gl.getUniformLocation(program, "c") };
}

export function Lumen({
  label,
  mode = "orb",
  intensity = 0.8,
  density = 0.8,
  hue = 0.45,
  breathPhase,
  lit = [],
  assemble = false,
  agitation = 0,
  lift = 0,
  spread = 0,
  className = "",
}: LumenProps) {
  const reducedMotion = useReducedMotion();
  const lowBandwidth = useLowBandwidth();
  const [gaveUp, setGaveUp] = useState(false);
  const [renderer, setRenderer] = useState<Renderer>("static");
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const live = useRef<Live>({ mode, intensity, density, hue, breathPhase, lit, agitation, lift, spread });
  useEffect(() => {
    live.current = { mode, intensity, density, hue, breathPhase, lit, agitation, lift, spread };
  });

  const animate = !reducedMotion && !lowBandwidth && !gaveUp;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!animate || !canvas) return;

    const webgl = createGl(canvas);
    const context2d = webgl ? null : canvas.getContext("2d");
    if (!webgl && !context2d) {
      queueMicrotask(() => setGaveUp(true));
      return;
    }
    queueMicrotask(() => setRenderer(webgl ? "webgl" : "canvas2d"));

    let particles = MAX_PARTICLES;
    const position = new Float32Array(MAX_PARTICLES * 2);
    const start = targets(live.current.mode, live.current.lit);
    for (let i = 0; i < MAX_PARTICLES; i += 1) {
      const scatter = assemble ? 1.5 + ((i * 37) % 100) / 60 : 1;
      const angle = assemble ? i * 0.61803 * Math.PI * 2 : 0;
      position[i * 2] = assemble ? Math.cos(angle) * scatter : start[i * 3]!;
      position[i * 2 + 1] = assemble ? Math.sin(angle) * scatter : start[i * 3 + 1]!;
    }
    const vertices = new Float32Array(MAX_PARTICLES * 4);

    let width = 0;
    let height = 0;
    let ratio = 1;
    const resize = () => {
      const box = canvas.getBoundingClientRect();
      ratio = Math.min(window.devicePixelRatio || 1, 2);
      width = Math.max(1, Math.round(box.width * ratio));
      height = Math.max(1, Math.round(box.height * ratio));
      canvas.width = width;
      canvas.height = height;
      webgl?.gl.viewport(0, 0, width, height);
    };
    resize();
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvas);

    let visible = true;
    const visibility = new IntersectionObserver(([entry]) => {
      visible = entry?.isIntersecting ?? true;
    });
    visibility.observe(canvas);

    let frame = 0;
    let handle = 0;
    let previous = performance.now();
    let sampleStart = previous;
    let sampled = 0;
    let stopped = false;

    const draw = (now: number) => {
      if (stopped) return;
      handle = requestAnimationFrame(draw);
      if (!visible || document.hidden) {
        previous = now;
        sampleStart = now;
        sampled = 0;
        return;
      }
      const delta = Math.min(64, now - previous);
      previous = now;
      frame += 1;

      // Frame-rate guard: degrade rather than stutter on slower phones.
      sampled += 1;
      if (frame > 30 && sampled >= 90) {
        const fps = (sampled * 1000) / (now - sampleStart);
        sampleStart = now;
        sampled = 0;
        if (fps < 50) {
          if (particles > MIN_PARTICLES) particles = Math.max(MIN_PARTICLES, particles >> 1);
          else {
            stopped = true;
            cancelAnimationFrame(handle);
            setGaveUp(true);
            return;
          }
        }
      }

      const state = live.current;
      const target = targets(state.mode, state.lit);
      const count = Math.round(particles * (0.35 + 0.65 * clamp01(state.density)));
      const scale = breathScale(state.breathPhase);
      const ease = 1 - Math.pow(0.93, delta / 16.7);
      const size = Math.min(width, height);
      const light = document.documentElement.dataset.theme === "daybreak";
      const [h, s, l] = lumenColor(state.hue, light);
      const half = size / 2;

      const restless = clamp01(state.agitation);
      const wobble = 0.011 * (1 + restless * 7);
      const scatter = 1 + clamp01(state.spread) * 0.55;
      const shift = state.lift * 0.18;
      for (let i = 0; i < count; i += 1) {
        const drift = now * 0.0005 * (1 + restless * 5) + i * 1.7;
        const tx = target[i * 3]! * scale * scatter + Math.sin(drift) * wobble;
        const ty = target[i * 3 + 1]! * scale * scatter + shift + Math.cos(drift * 1.3) * wobble;
        position[i * 2]! += (tx - position[i * 2]!) * ease;
        position[i * 2 + 1]! += (ty - position[i * 2 + 1]!) * ease;
        const alpha = level(target[i * 3 + 2]!, clamp01(state.intensity), i);
        vertices[i * 4] = position[i * 2]!;
        vertices[i * 4 + 1] = position[i * 2 + 1]!;
        vertices[i * 4 + 2] = (0.0065 + alpha * 0.0115) * size;
        vertices[i * 4 + 3] = alpha;
      }

      if (webgl) {
        const { gl, color } = webgl;
        const [r, g, b] = hslToRgb(h, s, l);
        gl.clearColor(0, 0, 0, 0);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.uniform3f(color, r, g, b);
        gl.bufferData(gl.ARRAY_BUFFER, vertices.subarray(0, count * 4), gl.DYNAMIC_DRAW);
        gl.drawArrays(gl.POINTS, 0, count);
      } else if (context2d) {
        context2d.clearRect(0, 0, width, height);
        context2d.fillStyle = `hsl(${h} ${s}% ${l}%)`;
        // One path per brightness level keeps canvas state changes to four a frame.
        for (let step = 1; step <= LEVELS; step += 1) {
          const alpha = step / LEVELS;
          context2d.globalAlpha = alpha;
          context2d.beginPath();
          for (let i = 0; i < count; i += 1) {
            if (vertices[i * 4 + 3] !== alpha) continue;
            const x = half + vertices[i * 4]! * half;
            const y = half + vertices[i * 4 + 1]! * half;
            const radius = vertices[i * 4 + 2]! / 2;
            context2d.moveTo(x + radius, y);
            context2d.arc(x, y, radius, 0, Math.PI * 2);
          }
          context2d.fill();
        }
      }
    };
    handle = requestAnimationFrame(draw);

    return () => {
      stopped = true;
      cancelAnimationFrame(handle);
      resizeObserver.disconnect();
      visibility.disconnect();
      setRenderer("static");
    };
  }, [animate, assemble]);

  // The static image: the same shape, fewer dots, no script needed.
  const dots = useMemo(() => {
    const target = targets(mode, lit, STATIC_DOTS);
    const scale = breathScale(breathPhase) * (1 + clamp01(spread) * 0.55);
    const shift = lift * 0.18;
    const shown = Math.round(STATIC_DOTS * (0.35 + 0.65 * clamp01(density)));
    return Array.from({ length: shown }, (_, i) => {
      const alpha = level(target[i * 3 + 2]!, clamp01(intensity), i);
      return {
        key: i,
        cx: (target[i * 3]! * scale).toFixed(3),
        cy: (target[i * 3 + 1]! * scale + shift).toFixed(3),
        r: (0.0085 + alpha * 0.0135).toFixed(4),
        opacity: alpha,
      };
    });
  }, [mode, lit, intensity, density, breathPhase, spread, lift]);
  const [h, s] = lumenColor(hue, false);
  const showCanvas = animate && renderer !== "static";

  return (
    <div
      role="img"
      aria-label={label}
      data-lumen={mode}
      data-renderer={showCanvas ? renderer : "static"}
      className={`relative aspect-square ${className}`}
    >
      <div aria-hidden="true" className="lumen-glow absolute inset-0" />
      <svg
        aria-hidden="true"
        viewBox="-1 -1 2 2"
        className="absolute inset-0 h-full w-full"
        style={{ visibility: showCanvas ? "hidden" : "visible", color: `hsl(${h} ${s}% var(--lumen-l, 76%))` }}
      >
        {dots.map((dot) => (
          <circle key={dot.key} cx={dot.cx} cy={dot.cy} r={dot.r} fill="currentColor" opacity={dot.opacity} />
        ))}
      </svg>
      {animate ? (
        <canvas ref={canvasRef} aria-hidden="true" className="absolute inset-0 h-full w-full" />
      ) : null}
    </div>
  );
}
