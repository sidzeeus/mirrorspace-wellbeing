"use client";

import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useSyncExternalStore } from "react";

import { ambient } from "@/lib/ambient";
import { setPrefs, usePrefs } from "@/lib/prefs";

/** Screens where the music falls silent: someone there may be on a call for help. */
const QUIET_PATHS = ["/support", "/offline"];

/**
 * Keeps the background music going across pages (it lives in the root layout, so it
 * is never restarted by navigation). Browsers forbid sound before the person interacts,
 * so it starts on the first tap, click or key press, if music is on.
 */
export function AmbientMusic() {
  const prefs = usePrefs();
  const pathname = usePathname();
  const on = prefs.music === "on";

  useEffect(() => {
    if (!on) {
      ambient.pause();
      return;
    }
    const start = () => ambient.play();
    window.addEventListener("pointerdown", start, { once: true });
    window.addEventListener("keydown", start, { once: true });
    return () => {
      window.removeEventListener("pointerdown", start);
      window.removeEventListener("keydown", start);
    };
  }, [on]);

  useEffect(() => {
    ambient.hush(QUIET_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`)));
  }, [pathname]);

  return null;
}

const noop = () => () => undefined;

/** The music button for the headers. A tap is the gesture that lets the sound start. */
export function MusicToggle({ className = "" }: { className?: string }) {
  const t = useTranslations("common.music");
  const prefs = usePrefs();
  const mounted = useSyncExternalStore(
    noop,
    () => true,
    () => false,
  );
  const on = mounted && prefs.music === "on";
  return (
    <button
      type="button"
      className={`inline-flex size-11 shrink-0 items-center justify-center rounded-full border border-line-strong text-moon hover:bg-raised ${className}`}
      aria-pressed={on}
      aria-label={on ? t("turnOff") : t("turnOn")}
      title={on ? t("turnOff") : t("turnOn")}
      onClick={() => {
        if (on) {
          setPrefs({ music: "off" });
          ambient.pause();
        } else {
          setPrefs({ music: "on" });
          ambient.play();
        }
      }}
      data-music-toggle
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M9 18V6l10-2v12M9 18a3 3 0 1 1-3-3 3 3 0 0 1 3 3Zm10-2a3 3 0 1 1-3-3 3 3 0 0 1 3 3Z"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {on ? null : <path d="M4 4l16 16" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />}
      </svg>
    </button>
  );
}
