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

export function AuroraBackground() {
  const prefs = usePrefs();
  const pathname = usePathname();
  const mounted = useSyncExternalStore(
    noop,
    () => true,
    () => false,
  );
  // Before hydration the CSS aurora on <body> is already showing; this fades in on top.
  if (!mounted) return null;
  const theme = resolveTheme(prefs.theme);
  const still = STILL_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));

  return (
    <div aria-hidden="true" className="no-print pointer-events-none fixed inset-0 -z-10">
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
    </div>
  );
}
