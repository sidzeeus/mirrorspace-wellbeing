"use client";

import { useSyncExternalStore } from "react";

const subscribe = (listener: () => void) => {
  window.addEventListener("hashchange", listener);
  return () => window.removeEventListener("hashchange", listener);
};

/**
 * Values from the URL fragment (after "#"). Emailed links put their token there
 * because browsers never send the fragment to a server, so it stays out of logs.
 * Returns null until the page has loaded in the browser.
 */
export function useFragment(): URLSearchParams | null {
  const hash = useSyncExternalStore(
    subscribe,
    () => window.location.hash,
    () => null,
  );
  return hash === null ? null : new URLSearchParams(hash.replace(/^#/, ""));
}
