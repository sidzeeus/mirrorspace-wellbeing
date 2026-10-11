"use client";

import { useTranslations } from "next-intl";
import { useSyncExternalStore } from "react";

import { IconButton } from "@/components/ui/primitives";
import { resolveTheme, setPrefs, usePrefs } from "@/lib/prefs";

const noop = () => () => undefined;

/** One press switches between Night and Daybreak and remembers the choice. */
export function ThemeToggle() {
  const t = useTranslations("common.theme");
  const prefs = usePrefs();
  const mounted = useSyncExternalStore(
    noop,
    () => true,
    () => false,
  );
  const current = mounted ? resolveTheme(prefs.theme) : "night";
  const next = current === "night" ? "daybreak" : "night";
  return (
    <IconButton
      label={next === "night" ? t("toNight") : t("toDaybreak")}
      onClick={() => setPrefs({ theme: next })}
    >
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        {current === "night" ? (
          <path d="M15.5 12.2A6.5 6.5 0 0 1 7.8 4.5a6.5 6.5 0 1 0 7.7 7.7Z" fill="currentColor" />
        ) : (
          <>
            <circle cx="10" cy="10" r="3.6" fill="currentColor" />
            <path
              d="M10 1.5v2.3M10 16.2v2.3M1.5 10h2.3M16.2 10h2.3M4 4l1.6 1.6M14.4 14.4 16 16M4 16l1.6-1.6M14.4 5.6 16 4"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinecap="round"
            />
          </>
        )}
      </svg>
    </IconButton>
  );
}
