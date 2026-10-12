import Link from "next/link";
import { useTranslations } from "next-intl";

import { ThemeToggle } from "@/components/ThemeToggle";

/** The quiet top bar on public pages: name, helplines, sign in, create, theme. */
export function PublicHeader() {
  const common = useTranslations("common");
  const t = useTranslations("landing.nav");
  return (
    <header className="glass sticky top-0 z-30 border-x-0 border-t-0 no-print">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-5 lg:px-10">
        <Link
          href="/"
          className="label inline-flex min-h-11 items-center border-x border-line-strong px-3 text-[0.8125rem] text-moon"
        >
          {common("appName")}
        </Link>
        <nav aria-label={common("appName")} className="flex items-center gap-1 sm:gap-2">
          {/* On the narrowest phones the header keeps only sign-in; helplines stay in the page. */}
          <Link href="/resources" className="nav-link hidden min-[400px]:inline-flex">
            {t("helplines")}
          </Link>
          <span aria-hidden="true" className="hidden text-dim min-[400px]:inline">
            ·
          </span>
          <Link href="/login" className="nav-link inline-flex">
            {t("signIn")}
          </Link>
          <Link href="/register" className="btn btn-quiet ml-2 hidden md:inline-flex">
            {t("create")}
          </Link>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
