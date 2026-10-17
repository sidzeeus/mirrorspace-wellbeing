"use client";

/**
 * AnimatedGradientBackground: a radial gradient that fades in and can slowly "breathe".
 *
 * Adapted from a community component (shadcn-style, framer-motion). Changes from the
 * original, to meet this app's rules (README Part C, docs/decisions.md B70):
 * - With reduced motion or low-bandwidth mode it is a still gradient: no entrance
 *   animation and no animation loop.
 * - The loop only runs while breathing, and pauses when the tab is hidden; a still
 *   gradient is painted once instead of on every frame.
 * - It is decoration, so it is hidden from screen readers.
 * - framer-motion is loaded through `LazyMotion` with only its basic animation
 *   features, which keeps it small enough to sit on every page.
 */
import { LazyMotion, domAnimation, m } from "framer-motion";
import type React from "react";
import { useEffect, useRef } from "react";

import { useLowBandwidth, useReducedMotion } from "@/lib/prefs";

interface AnimatedGradientBackgroundProps {
  /**
   * Initial size of the radial gradient, defining the starting width.
   * @default 125
   */
  startingGap?: number;

  /**
   * Enables or disables the breathing animation effect.
   * @default false
   */
  Breathing?: boolean;

  /**
   * Array of colors to use in the radial gradient.
   * Each color corresponds to a stop percentage in `gradientStops`.
   * @default ["#0A0A0A", "#2979FF", "#FF80AB", "#FF6D00", "#FFD600", "#00E676", "#3D5AFE"]
   */
  gradientColors?: string[];

  /**
   * Array of percentage stops corresponding to each color in `gradientColors`.
   * The values should range between 0 and 100.
   * @default [35, 50, 60, 70, 80, 90, 100]
   */
  gradientStops?: number[];

  /**
   * Speed of the breathing animation. Lower values result in slower animation.
   * @default 0.02
   */
  animationSpeed?: number;

  /**
   * Maximum range for the breathing animation in percentage points.
   * @default 5
   */
  breathingRange?: number;

  /**
   * Additional inline styles for the gradient container.
   * @default {}
   */
  containerStyle?: React.CSSProperties;

  /**
   * Additional class names for the gradient container.
   * @default ""
   */
  containerClassName?: string;

  /**
   * Additional top offset, for more control over the gradient's vertical size.
   * @default 0
   */
  topOffset?: number;
}

const DEFAULT_COLORS = ["#0A0A0A", "#2979FF", "#FF80AB", "#FF6D00", "#FFD600", "#00E676", "#3D5AFE"];
const DEFAULT_STOPS = [35, 50, 60, 70, 80, 90, 100];

const AnimatedGradientBackground: React.FC<AnimatedGradientBackgroundProps> = ({
  startingGap = 125,
  Breathing = false,
  gradientColors = DEFAULT_COLORS,
  gradientStops = DEFAULT_STOPS,
  animationSpeed = 0.02,
  breathingRange = 5,
  containerStyle = {},
  topOffset = 0,
  containerClassName = "",
}) => {
  if (gradientColors.length !== gradientStops.length) {
    throw new Error(
      `GradientColors and GradientStops must have the same length.
     Received gradientColors length: ${gradientColors.length},
     gradientStops length: ${gradientStops.length}`,
    );
  }

  const reducedMotion = useReducedMotion();
  const lowBandwidth = useLowBandwidth();
  const still = reducedMotion || lowBandwidth;
  const breathing = Breathing && !still;
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Compared by value, so callers passing fresh arrays each render do not restart it.
  const colorsKey = gradientColors.join("|");
  const stopsKey = gradientStops.join("|");

  useEffect(() => {
    const colors = colorsKey.split("|");
    const stops = stopsKey.split("|").map(Number);
    const gradientStopsString = stops.map((stop, index) => `${colors[index]} ${stop}%`).join(", ");
    const paint = (width: number) => {
      if (containerRef.current) {
        containerRef.current.style.background = `radial-gradient(${width}% ${width + topOffset}% at 50% 20%, ${gradientStopsString})`;
      }
    };

    paint(startingGap);
    if (!breathing) return;

    let animationFrame = 0;
    let width = startingGap;
    let directionWidth = 1;
    const animateGradient = () => {
      animationFrame = requestAnimationFrame(animateGradient);
      if (document.hidden) return;
      if (width >= startingGap + breathingRange) directionWidth = -1;
      if (width <= startingGap - breathingRange) directionWidth = 1;
      width += directionWidth * animationSpeed;
      paint(width);
    };
    animationFrame = requestAnimationFrame(animateGradient);
    return () => cancelAnimationFrame(animationFrame);
  }, [startingGap, breathing, colorsKey, stopsKey, animationSpeed, breathingRange, topOffset]);

  return (
    <LazyMotion features={domAnimation} strict>
      <m.div
      key="animated-gradient-background"
      aria-hidden="true"
      initial={still ? false : { opacity: 0, scale: 1.5 }}
      animate={{
        opacity: 1,
        scale: 1,
        transition: { duration: 2, ease: [0.25, 0.1, 0.25, 1] },
      }}
      className={`absolute inset-0 overflow-hidden ${containerClassName}`}
    >
      <div ref={containerRef} style={containerStyle} className="absolute inset-0 transition-transform" />
      </m.div>
    </LazyMotion>
  );
};

export default AnimatedGradientBackground;
