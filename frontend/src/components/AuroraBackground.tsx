"use client";

import { usePathname } from "next/navigation";
import { useSyncExternalStore } from "react";

import AnimatedGradientBackground from "@/components/ui/animated-gradient-background";
import { resolveTheme, usePrefs } from "@/lib/prefs";

/*
  The aurora behind every page. These match `--aurora` in globals.css, which paints the
  same gradient without JavaScript; keep the two in step.
*/
const STOPS = [32, 46, 57, 68, 78, 89, 100];
const COLORS = {
  night: ["#07060d", "#1a1546", "#2d2584", "#4a33a0", "#5e3184", "#1b5f66", "#262273"],
  daybreak: ["#f7f5fc", "#ece6ff", "#d9ceff", "#ecd2f5", "#f8d8e6", "#cdeee7", "#dcd8ff"],
};

/** Screens where nothing may move unless the person starts it (Support, offline). */
const STILL_PATHS = ["/support", "/offline"];

const noop = () => () => undefined;

/*
  Small stars in the dark upper sky. Placed with a fixed seed, so the server and the
  browser draw the same sky. Each twinkles slowly at its own pace (globals.css, "Stars").
*/
function seeded(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const random = seeded(2026);
const STARS = Array.from({ length: 90 }, (_, index) => {
  const size = random() < 0.12 ? 4.5 : random() < 0.5 ? 3 : 2;
  return {
    key: index,
    left: `${(random() * 100).toFixed(2)}%`,
    top: `${(random() * 62).toFixed(2)}%`,
    size,
    duration: `${(3.5 + random() * 5).toFixed(1)}s`,
    delay: `${(-random() * 8).toFixed(1)}s`,
    dim: (0.35 + random() * 0.5).toFixed(2),
  };
});

function Stars({ still }: { still: boolean }) {
  return (
    <div className={`stars absolute inset-0 ${still ? "stars-still" : ""}`}>
      {STARS.map((star) => (
        <span
          key={star.key}
          className="star"
          style={{
            left: star.left,
            top: star.top,
            width: star.size,
            height: star.size,
            animationDuration: star.duration,
            animationDelay: star.delay,
            ["--star-dim" as string]: star.dim,
          }}
        />
      ))}
    </div>
  );
}

/*
  Light theme: soft dark bubbles that drift up the screen and pop near the top
  (globals.css, "Bubbles"). Fixed seed, like the stars.
*/
const BUBBLES = Array.from({ length: 28 }, (_, index) => ({
  key: index,
  left: `${(random() * 100).toFixed(2)}%`,
  size: Math.round(10 + random() * 26),
  duration: `${(14 + random() * 14).toFixed(1)}s`,
  delay: `${(-random() * 28).toFixed(1)}s`,
  sway: `${Math.round((random() - 0.5) * 60)}px`,
}));

function Bubbles({ still }: { still: boolean }) {
  return (
    <div className={`bubbles absolute inset-0 overflow-hidden ${still ? "bubbles-still" : ""}`}>
      {BUBBLES.map((bubble) => (
        <span
          key={bubble.key}
          className="bubble"
          style={{
            left: bubble.left,
            width: bubble.size,
            height: bubble.size,
            animationDuration: bubble.duration,
            animationDelay: bubble.delay,
            ["--bubble-sway" as string]: bubble.sway,
          }}
        />
      ))}
    </div>
  );
}

export function AuroraBackground() {
  const prefs = usePrefs();
  const pathname = usePathname();
  const mounted = useSyncExternalStore(
    noop,
    () => true,
    () => false,
  );
  const still = STILL_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
  // Before hydration the CSS aurora on <body> is already showing; the moving one fades in.
  const theme = mounted ? resolveTheme(prefs.theme) : null;

  return (
    <div aria-hidden="true" className="no-print pointer-events-none fixed inset-0 -z-10">
      {theme ? (
        <AnimatedGradientBackground
          key={theme}
          Breathing={!still}
          startingGap={105}
          breathingRange={6}
          animationSpeed={0.015}
          topOffset={10}
          gradientColors={COLORS[theme]}
          gradientStops={STOPS}
        />
      ) : null}
      <Stars still={still} />
      <Bubbles still={still} />
    </div>
  );
}
