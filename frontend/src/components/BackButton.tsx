"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import { useMe } from "@/lib/hooks";

/**
 * Goes back to wherever the person came from in this app. Opened directly (a link from
 * outside, a bookmark), there is nowhere to go back to, so it goes to Home when signed
 * in and to the start page otherwise.
 */
export function BackButton({ className = "" }: { className?: string }) {
  const t = useTranslations("common");
  const router = useRouter();
  const me = useMe();
  const fallback = me.data ? "/home" : "/";
  return (
    <button
      type="button"
      className={`btn btn-quiet ${className}`}
      onClick={() => {
        const cameFromHere =
          window.history.length > 1 && document.referrer.startsWith(window.location.origin);
        if (cameFromHere) router.back();
        else router.push(fallback);
      }}
      data-back
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M15 6l-6 6 6 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {t("back")}
    </button>
  );
}
