"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { type ReactNode, useEffect } from "react";

import { Button } from "@/components/ui/primitives";
import { ApiError, api, forgetCsrfToken } from "@/lib/api";
import { PRIVACY_PURPOSE } from "@/lib/constants";
import { useConsents, useMe, useNotices } from "@/lib/hooks";
import { clearOfflineCopies } from "@/lib/offline";

const ICONS: Record<string, ReactNode> = {
  home: <path d="M4 11 12 4l8 7v8h-5v-5H9v5H4z" />,
  checkIn: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="m8.5 12 2.5 2.5 4.5-5" />
    </>
  ),
  patterns: <path d="M4 4v16h16M7 15l4-4 3 3 5-6" />,
  episodes: (
    <>
      <path d="M5 5h14v14H5z" />
      <path d="M8 9h8M8 13h5" />
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
  sharing: (
    <>
      <circle cx="8" cy="9" r="3" />
      <circle cx="16" cy="9" r="3" />
      <path d="M3 19c.8-3 2.7-4.5 5-4.5s4.2 1.5 5 4.5M14 15c.6-.3 1.3-.5 2-.5 2.3 0 4.2 1.5 5 4.5" />
    </>
  ),
  chat: <path d="M5 5h14v10h-7l-4 4v-4H5z" />,
  resources: (
    <path d="M7 4h3l1 4-2 1.5a10 10 0 0 0 5.5 5.5L16 13l4 1v3a2 2 0 0 1-2 2A14 14 0 0 1 5 6a2 2 0 0 1 2-2Z" />
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4" />
    </>
  ),
};

/** Every part of the app, always in view. Nothing is tucked away in a menu. */
const NAV = [
  { key: "home", href: "/home" },
  { key: "checkIn", href: "/check-in" },
  { key: "patterns", href: "/patterns" },
  { key: "episodes", href: "/episodes" },
  { key: "exercises", href: "/exercises" },
  { key: "plan", href: "/plan" },
  { key: "sharing", href: "/sharing" },
  { key: "chat", href: "/chat" },
  { key: "resources", href: "/resources" },
  { key: "settings", href: "/settings" },
] as const;

/**
 * The SOS button: a plain link to Support, present on every screen, never inside a
 * menu. Because it is a link and not a script-driven dialog, it works offline and
 * before scripts load. Pressing it sends nothing; Support shows the choices.
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
      <span className="font-semibold tracking-[0.16em]">{t("sos")}</span>
      <span>{t("support")}</span>
    </a>
  );
}

/** Signing out leaves nothing of this person on the device. */
export function SignOut({ className = "" }: { className?: string }) {
  const t = useTranslations("shell");
  const queryClient = useQueryClient();
  const signOut = useMutation({
    mutationFn: () => api("/auth/logout", { method: "POST" }),
    onSettled: () => {
      clearOfflineCopies();
      forgetCsrfToken();
      queryClient.clear();
      // A full page load, on purpose: it drops everything held in memory.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign("/");
    },
  });
  return (
    <Button variant="quiet" className={className} busy={signOut.isPending} onClick={() => signOut.mutate()}>
      {t("signOut")}
    </Button>
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
      className={`flex min-h-11 items-center ${
        vertical
          ? "gap-3 border-l-2 px-3 text-sm"
          : "flex-col justify-center gap-0.5 border-t-2 px-0.5 py-1 text-center text-[0.6875rem] leading-tight"
      } ${current ? "border-moon bg-raised text-moon" : "border-transparent text-dim hover:text-moon"}`}
    >
      <svg
        width={vertical ? 20 : 18}
        height={vertical ? 20 : 18}
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
 * The signed-in frame: every section in a two-row bar on phones and in a left rail on
 * desktop, with the SOS button at the top of every screen. It also sends people who
 * are signed out to sign in, and people who have not yet accepted the current notice
 * to onboarding.
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
      <aside className="no-print hidden border-r border-line lg:sticky lg:top-0 lg:flex lg:h-dvh lg:flex-col lg:overflow-y-auto lg:p-5">
        <Link
          href="/home"
          className="label mb-6 inline-flex min-h-11 items-center self-start border-x border-line-strong px-3 text-[0.8125rem] text-moon"
        >
          {common("appName")}
        </Link>
        <SupportLink className="mb-6 w-full" />
        {onboarding ? null : (
          <nav aria-label={t("navLabel")} className="flex flex-col gap-0.5">
            {NAV.map((item) => (
              <NavLink key={item.key} item={item} vertical />
            ))}
          </nav>
        )}
      </aside>

      <div className="flex min-h-dvh flex-col">
        <header className="glass no-print sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-x-0 border-t-0 px-5 lg:hidden">
          <Link
            href="/home"
            className="label inline-flex min-h-11 items-center border-x border-line-strong px-3 text-[0.8125rem] text-moon"
          >
            {common("appName")}
          </Link>
          <SupportLink />
        </header>

        <main
          id="main"
          className="page-fade mx-auto w-full max-w-3xl grow px-5 pb-40 pt-8 lg:pb-16 lg:pt-12"
        >
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
            className="glass no-print fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-x-0 border-b-0 pb-[env(safe-area-inset-bottom)] lg:hidden"
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
