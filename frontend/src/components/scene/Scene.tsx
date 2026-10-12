"use client";

/**
 * A dithered scene of light: the large imagery on the public pages.
 * See docs/design-plan.md, "Scenes".
 *
 * Rendering chain, like the Lumen's:
 *   1. A still image (CSS background, public/scenes). Works without JavaScript and is
 *      what reduced-motion users keep. Low-bandwidth mode downloads nothing at all.
 *   2. A canvas that draws the same picture and lets it shimmer and breathe slowly.
 *      It pauses off screen, and stops for good if the device cannot keep up.
 *
 * It is an illustration, never information: nothing here reflects anyone's data.
 */
import { useEffect, useRef, useState } from "react";

import { useLowBandwidth, useReducedMotion } from "@/lib/prefs";

import { PALETTE, type SceneName, TONES, sample, tone } from "./fields";

const CELL = 4; // CSS pixels per dot cell
const FRAME_MS = 90; // about 11 frames a second: a shimmer, not an animation
const SLOW_FRAME_MS = 28; // drawing time above this, three times running, stops it

export type SceneProps = {
  scene: SceneName;
  /** What the picture shows, for screen readers. */
  label: string;
  className?: string;
};

export function Scene({ scene, label, className = "" }: SceneProps) {
  const reducedMotion = useReducedMotion();
  const lowBandwidth = useLowBandwidth();
  const [gaveUp, setGaveUp] = useState(false);
  const [drawing, setDrawing] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animate = !reducedMotion && !lowBandwidth && !gaveUp;

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = animate && canvas ? canvas.getContext("2d") : null;
    if (!canvas || !context) return;

    let columns = 0;
    let rows = 0;
    let ratio = 1;
    let still = new Float32Array(0);
    let glow = new Float32Array(0);

    const measure = () => {
      const box = canvas.getBoundingClientRect();
      if (box.width < 2 || box.height < 2) return;
      ratio = Math.min(window.devicePixelRatio || 1, 2);
      columns = Math.ceil(box.width / CELL);
      rows = Math.ceil(box.height / CELL);
      canvas.width = Math.round(columns * CELL * ratio);
      canvas.height = Math.round(rows * CELL * ratio);
      const aspect = box.width / box.height;
      still = new Float32Array(columns * rows);
      glow = new Float32Array(columns * rows);
      for (let j = 0; j < rows; j += 1) {
        for (let i = 0; i < columns; i += 1) {
          const x = (((i + 0.5) / columns) * 2 - 1) * aspect;
          const y = ((j + 0.5) / rows) * 2 - 1;
          const value = sample(scene, x, y, aspect);
          still[j * columns + i] = value.still;
          glow[j * columns + i] = value.glow;
        }
      }
    };
    measure();
    const resizeObserver = new ResizeObserver(measure);
    resizeObserver.observe(canvas);

    let visible = true;
    const visibility = new IntersectionObserver(([entry]) => {
      visible = entry?.isIntersecting ?? true;
    });
    visibility.observe(canvas);

    let handle = 0;
    let last = 0;
    let slow = 0;
    let stopped = false;
    let first = true;
    const buckets: number[][] = Array.from({ length: TONES }, () => []);

    const draw = (now: number) => {
      if (stopped) return;
      handle = requestAnimationFrame(draw);
      if (!visible || document.hidden || now - last < FRAME_MS || columns === 0) return;
      last = now;
      const started = performance.now();

      const breath = 1 + 0.14 * Math.sin(now / 1900);
      const drift = (now / 26000) % 1;
      for (const bucket of buckets) bucket.length = 0;
      for (let j = 0; j < rows; j += 1) {
        for (let i = 0; i < columns; i += 1) {
          const at = j * columns + i;
          const index = tone(still[at]! + glow[at]! * breath, i, j, drift);
          if (index >= 0) buckets[index]!.push(i, j);
        }
      }

      const palette =
        PALETTE[document.documentElement.dataset.theme === "daybreak" ? "daybreak" : "night"];
      const cell = CELL * ratio;
      const dot = Math.max(1, Math.round(cell * 0.62));
      context.clearRect(0, 0, canvas.width, canvas.height);
      buckets.forEach((bucket, index) => {
        const [r, g, b] = palette[index]!;
        context.fillStyle = `rgb(${r} ${g} ${b})`;
        for (let n = 0; n < bucket.length; n += 2) {
          context.fillRect(Math.round(bucket[n]! * cell), Math.round(bucket[n + 1]! * cell), dot, dot);
        }
      });
      if (first) {
        first = false;
        setDrawing(true);
      }

      // Never make a slow phone slower for the sake of a picture.
      slow = performance.now() - started > SLOW_FRAME_MS ? slow + 1 : 0;
      if (slow >= 3) {
        stopped = true;
        cancelAnimationFrame(handle);
        setGaveUp(true);
      }
    };
    handle = requestAnimationFrame(draw);

    return () => {
      stopped = true;
      cancelAnimationFrame(handle);
      resizeObserver.disconnect();
      visibility.disconnect();
      setDrawing(false);
    };
  }, [animate, scene]);

  const live = animate && drawing;
  return (
    <div
      role="img"
      aria-label={label}
      data-scene={scene}
      data-renderer={live ? "canvas" : "still"}
      className={`relative overflow-hidden ${className}`}
    >
      <div
        aria-hidden="true"
        data-scene-still={scene}
        className="scene-still absolute inset-0"
        style={{ visibility: live ? "hidden" : "visible" }}
      />
      {animate ? (
        <canvas ref={canvasRef} aria-hidden="true" className="absolute inset-0 h-full w-full" />
      ) : null}
    </div>
  );
}
