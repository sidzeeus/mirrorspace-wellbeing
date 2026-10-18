"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { WAKING_EVENT } from "@/lib/api";

/**
 * Shown while the API is starting up after a quiet spell (the free host sleeps when
 * idle). Requests are retried meanwhile, so the person only needs to wait.
 */
export function WakingNotice() {
  const t = useTranslations("common");
  const [waking, setWaking] = useState(false);

  useEffect(() => {
    const listener = (event: Event) => setWaking(Boolean((event as CustomEvent<boolean>).detail));
    window.addEventListener(WAKING_EVENT, listener);
    return () => window.removeEventListener(WAKING_EVENT, listener);
  }, []);

  return (
    <div
      role="status"
      data-waking={waking || undefined}
      className="no-print pointer-events-none fixed inset-x-3 top-20 z-40 flex justify-center"
    >
      {waking ? (
        <p className="glass max-w-md rounded-2xl px-4 py-3 text-center text-[0.9375rem]">
          {t("waking")}
        </p>
      ) : null}
    </div>
  );
}
