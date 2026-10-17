"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

import { MusicToggle } from "@/components/AmbientMusic";
import { CatFace } from "@/components/pet/CatFace";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useMe } from "@/lib/hooks";

/**
 * The floating bar on public pages. Signed out: name, helplines, sign in, create,
 * theme. Signed in (for example on Helplines, which is public), the name and a "Back
 * to the app" button lead back into the app instead of to the sign-up page.
 */
export function PublicHeader() {
  const common = useTranslations("common");
  const t = useTranslations("landing.nav");
  const me = useMe();
  const signedIn = Boolean(me.data);
  return (
    <header className="no-print sticky top-0 z-30 px-3 pt-3 sm:px-5">
      <div className="glass mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 rounded-full py-1 pl-5 pr-2">
        <Link
          href={signedIn ? "/home" : "/"}
          className="inline-flex min-h-11 items-center gap-2 text-lg font-medium tracking-tight"
        >
          <CatFace expression="happy" className="w-8" />
          <span className="sr-only min-[360px]:not-sr-only">{common("appName")}</span>
        </Link>
        <nav aria-label={common("appName")} className="flex items-center gap-1">
          {signedIn ? (
            <Link href="/home" className="btn btn-primary" data-back-to-app>
              {t("backToApp")}
            </Link>
          ) : (
            <>
              {/* On the narrowest phones the header keeps only sign-in; helplines stay in the page. */}
              <Link href="/resources" className="nav-link hidden min-[400px]:inline-flex">
                {t("helplines")}
              </Link>
              <Link href="/login" className="nav-link inline-flex">
                {t("signIn")}
              </Link>
              <Link href="/register" className="btn btn-primary ml-1 hidden md:inline-flex">
                {t("create")}
              </Link>
            </>
          )}
          <MusicToggle />
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
