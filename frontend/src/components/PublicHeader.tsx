import Link from "next/link";
import { useTranslations } from "next-intl";

import { ThemeToggle } from "@/components/ThemeToggle";

/** The quiet top bar on public pages: name, helplines, sign in, theme. */
export function PublicHeader() {
  const common = useTranslations("common");
  const t = useTranslations("landing.nav");
  return (
    <header className="glass sticky top-0 z-30 border-x-0 border-t-0 no-print">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-5">
        <Link href="/" className="inline-flex min-h-11 items-center text-lg font-medium tracking-tight">
          {common("appName")}
        </Link>
        <nav aria-label={common("appName")} className="flex items-center gap-1 sm:gap-3">
          <Link href="/resources" className="btn-text inline-flex items-center px-2 no-underline">
            {t("helplines")}
          </Link>
          <Link href="/login" className="btn-text inline-flex items-center px-2 no-underline">
            {t("signIn")}
          </Link>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
