"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { type ReactNode, useEffect } from "react";

import { ApiError } from "@/lib/api";
import { PRIVACY_PURPOSE } from "@/lib/constants";
import { useConsents, useMe, useNotices } from "@/lib/hooks";

const ICONS: Record<string, ReactNode> = {
  home: <path d="M4 11 12 4l8 7v8h-5v-5H9v5H4z" />,
  checkIn: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="m8.5 12 2.5 2.5 4.5-5" />
    </>
  ),
  exercises: (
    <>
      <circle cx="12" cy="12" r="3" />
      <circle cx="12" cy="12" r="8" strokeDasharray="2 3" />
    </>
  ),
  plan: (
    <>
      <path d="M7 4h10v16H7z" />
      <path d="M10 9h4M10 13h4" />
    </>
  ),
  more: (
    <>
      <circle cx="6" cy="12" r="1" />
      <circle cx="12" cy="12" r="1" />
      <circle cx="18" cy="12" r="1" />
    </>
  ),
};

const NAV = [
  { key: "home", href: "/home" },
  { key: "checkIn", href: "/check-in" },
  { key: "exercises", href: "/exercises" },
  { key: "plan", href: "/plan" },
  { key: "more", href: "/more" },
] as const;

/**
 * Support is a plain link, present on every screen, never inside a menu. Because it is
 * a link and not a script-driven dialog, it works offline and before scripts load.
 */
export function SupportLink({ className = "" }: { className?: string }) {
  const t = useTranslations("common");
  return (
    <a href="/support" className={`btn btn-care no-print ${className}`} data-support-link>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10Z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
      </svg>
      {t("support")}
    </a>
  );
}

function NavLink({ item, vertical }: { item: (typeof NAV)[number]; vertical: boolean }) {
  const t = useTranslations("shell");
  const pathname = usePathname();
  const current = pathname === item.href || pathname.startsWith(`${item.href}/`);
  return (
    <Link
      href={item.href}
      aria-current={current ? "page" : undefined}
      className={`flex min-h-12 items-center gap-3 rounded-[14px] ${
        vertical ? "px-3" : "grow flex-col justify-center gap-0.5 px-1 py-1.5 text-xs"
      } ${current ? "bg-raised text-moon" : "text-dim hover:text-moon"}`}
    >
      <svg
        width="22"
        height="22"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        {ICONS[item.key]}
      </svg>
      <span>{t(item.key)}</span>
    </Link>
  );
}

/**
 * The signed-in frame: bottom navigation on phones, a slim left rail on desktop.
 * It also sends people who are signed out to sign in, and people who have not yet
 * accepted the current notice to onboarding.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const t = useTranslations("shell");
  const common = useTranslations("common");
  const router = useRouter();
  const pathname = usePathname();
  const me = useMe();
  const signedIn = Boolean(me.data);
  const consents = useConsents(signedIn);
  const notices = useNotices(signedIn);

  const accepted =
    consents.data && notices.data
      ? consents.data.results.some(
          (consent) =>
            consent.purpose === PRIVACY_PURPOSE &&
            consent.notice_version === notices.data.privacy_notice_version,
        )
      : null;
  const onboarding = pathname === "/onboarding";

  useEffect(() => {
    if (me.isSuccess && me.data === null) router.replace("/login");
    else if (accepted === false && !onboarding) router.replace("/onboarding");
    else if (accepted === true && onboarding) router.replace("/home");
  }, [me.isSuccess, me.data, accepted, onboarding, router]);

  // With no connection the session cannot be checked. The pages are still shown so the
  // copies kept on this device (safety plan, exercises) stay reachable; every request
  // for anything else simply fails and says so.
  const offline = me.isError && me.error instanceof ApiError && me.error.status === 0;
  const ready = offline || (signedIn && accepted !== null && (accepted || onboarding));

  return (
    <div className="lg:grid lg:min-h-dvh lg:grid-cols-[15rem_minmax(0,1fr)]">
      <aside className="no-print hidden border-r border-line lg:flex lg:flex-col lg:p-5">
        <Link href="/home" className="mb-8 inline-flex min-h-11 items-center px-3 text-lg font-medium">
          {common("appName")}
        </Link>
        {onboarding ? null : (
          <nav aria-label={t("navLabel")} className="flex flex-col gap-1">
            {NAV.map((item) => (
              <NavLink key={item.key} item={item} vertical />
            ))}
          </nav>
        )}
        <SupportLink className="mt-auto" />
      </aside>

      <div className="flex min-h-dvh flex-col">
        <header className="glass no-print sticky top-0 z-30 flex h-16 items-center justify-between border-x-0 border-t-0 px-5 lg:hidden">
          <Link href="/home" className="inline-flex min-h-11 items-center text-lg font-medium">
            {common("appName")}
          </Link>
          <SupportLink />
        </header>

        <main id="main" className="page-fade mx-auto w-full max-w-3xl grow px-5 pb-28 pt-8 lg:pb-16 lg:pt-12">
          {ready ? (
            children
          ) : (
            <p role="status" className="text-dim">
              {me.isError ? common("errors.unreachable") : t("loading")}
            </p>
          )}
        </main>

        {onboarding ? null : (
          <nav
            aria-label={t("navLabel")}
            className="glass no-print fixed inset-x-0 bottom-0 z-30 flex border-x-0 border-b-0 px-2 pb-[env(safe-area-inset-bottom)] lg:hidden"
          >
            {NAV.map((item) => (
              <NavLink key={item.key} item={item} vertical={false} />
            ))}
          </nav>
        )}
      </div>
    </div>
  );
}
