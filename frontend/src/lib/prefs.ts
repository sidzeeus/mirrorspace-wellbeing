"use client";

/**
 * Device preferences: theme, text size, motion and data use.
 *
 * These are comforts of one device, not account data, so they live in this browser
 * only (localStorage) and are never sent to the server. They are applied as
 * attributes on <html>, which is what the CSS in globals.css keys off.
 */
import { useSyncExternalStore } from "react";

export type Theme = "system" | "night" | "daybreak";
export type Prefs = {
  theme: Theme;
  text: "normal" | "large";
  motion: "system" | "reduced";
  bandwidth: "auto" | "low";
};

export const DEFAULT_PREFS: Prefs = {
  theme: "system",
  text: "normal",
  motion: "system",
  bandwidth: "auto",
};

export const PREFS_KEY = "prefs";

const listeners = new Set<() => void>();
let cached: Prefs = DEFAULT_PREFS;
let cachedRaw: string | null = null;

function read(): Prefs {
  let raw: string | null = null;
  try {
    raw = window.localStorage.getItem(PREFS_KEY);
  } catch {
    return DEFAULT_PREFS;
  }
  if (raw === cachedRaw) return cached;
  cachedRaw = raw;
  try {
    cached = { ...DEFAULT_PREFS, ...(raw ? (JSON.parse(raw) as Partial<Prefs>) : {}) };
  } catch {
    cached = DEFAULT_PREFS;
  }
  return cached;
}

export function resolveTheme(theme: Theme): "night" | "daybreak" {
  if (theme !== "system") return theme;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "daybreak" : "night";
}

/** Slow or metered connection reported by the browser. */
export function connectionIsConstrained(): boolean {
  const connection = (
    navigator as Navigator & { connection?: { saveData?: boolean; effectiveType?: string } }
  ).connection;
  return Boolean(connection?.saveData) || /(^|-)2g$/.test(connection?.effectiveType ?? "");
}

export function applyPrefs(prefs: Prefs): void {
  const root = document.documentElement;
  root.dataset.theme = resolveTheme(prefs.theme);
  root.dataset.text = prefs.text;
  if (prefs.motion === "reduced") root.dataset.motion = "reduced";
  else delete root.dataset.motion;
  if (prefs.bandwidth === "low" || connectionIsConstrained()) root.dataset.bandwidth = "low";
  else delete root.dataset.bandwidth;
}

export function setPrefs(change: Partial<Prefs>): void {
  const next = { ...read(), ...change };
  try {
    window.localStorage.setItem(PREFS_KEY, JSON.stringify(next));
  } catch {
    // Private browsing can refuse storage; the choice then lasts for this page only.
  }
  cachedRaw = JSON.stringify(next);
  cached = next;
  applyPrefs(next);
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  const media = [
    window.matchMedia("(prefers-color-scheme: light)"),
    window.matchMedia("(prefers-reduced-motion: reduce)"),
  ];
  const onChange = () => {
    applyPrefs(read());
    listener();
  };
  media.forEach((query) => query.addEventListener("change", onChange));
  window.addEventListener("storage", onChange);
  return () => {
    listeners.delete(listener);
    media.forEach((query) => query.removeEventListener("change", onChange));
    window.removeEventListener("storage", onChange);
  };
}

export function usePrefs(): Prefs {
  return useSyncExternalStore(subscribe, read, () => DEFAULT_PREFS);
}

/** True when animation should be replaced by a static state. */
export function useReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribe,
    () =>
      read().motion === "reduced" ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => true,
  );
}

/** True when canvases, web fonts and other heavy assets should be skipped. */
export function useLowBandwidth(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => read().bandwidth === "low" || connectionIsConstrained(),
    () => true,
  );
}

/**
 * Runs in <head> before first paint so the page never flashes the wrong theme.
 * Kept as a string because it must execute before React loads.
 */
export const PREFS_BOOT_SCRIPT = `(function(){try{var p=JSON.parse(localStorage.getItem(${JSON.stringify(
  PREFS_KEY,
)})||"{}"),d=document.documentElement,t=p.theme||"system";d.dataset.theme=t==="system"?(matchMedia("(prefers-color-scheme: light)").matches?"daybreak":"night"):t;d.dataset.text=p.text||"normal";if(p.motion==="reduced")d.dataset.motion="reduced";var c=navigator.connection||{};if(p.bandwidth==="low"||c.saveData||/(^|-)2g$/.test(c.effectiveType||""))d.dataset.bandwidth="low";}catch(e){document.documentElement.dataset.theme="night";}})();`;
