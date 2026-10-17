import Link from "next/link";
import { useTranslations } from "next-intl";

import { ThemeToggle } from "@/components/ThemeToggle";

/** The floating bar on public pages: name, helplines, sign in, create, theme. */
export function PublicHeader() {
  const common = useTranslations("common");
  const t = useTranslations("landing.nav");
  return (
    <header className="no-print sticky top-0 z-30 px-3 pt-3 sm:px-5">
      <div className="glass mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 rounded-full py-1 pl-5 pr-2">
        <Link href="/" className="inline-flex min-h-11 items-center text-lg font-medium tracking-tight">
          {common("appName")}
        </Link>
        <nav aria-label={common("appName")} className="flex items-center gap-1">
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
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
