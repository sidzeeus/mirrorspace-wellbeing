import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { HelplineStrip } from "@/components/landing/HelplineStrip";
import { Story } from "@/components/landing/Story";
import { PublicHeader } from "@/components/PublicHeader";
import { Scene } from "@/components/scene/Scene";
import { buttonClass } from "@/components/ui/primitives";

const ITEMS = ["a", "b", "c", "d"] as const;

export default async function LandingPage() {
  const t = await getTranslations("landing");
  const steps = (["one", "two", "three"] as const).map((key) => ({
    title: t(`story.${key}.title`),
    body: t(`story.${key}.body`),
    lumen: t(`story.${key}.lumen`),
  }));

  return (
    <>
      <PublicHeader />

      <main id="main">
        {/* The stage: one picture of held light, with the promise set low and left. */}
        <section className="relative isolate flex min-h-[calc(100svh-4rem)] flex-col overflow-hidden border-b border-line">
          <Scene scene="held" label={t("hero.lumen")} className="absolute! inset-0 -z-20" />
          <div aria-hidden="true" className="absolute inset-y-0 left-1/2 -z-10 w-px bg-line" />
          <div aria-hidden="true" className="absolute inset-x-0 top-[58%] -z-10 h-px bg-line" />

          <div className="mt-auto bg-gradient-to-t from-ink via-ink/80 to-transparent pt-16">
            <div className="mx-auto grid max-w-7xl gap-8 px-5 pb-8 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end lg:gap-16 lg:px-10">
              <div className="marks max-w-3xl">
                <p className="label mb-5 text-dim">{t("hero.eyebrow")}</p>
                <h1 className="hero-title mb-5">
                  <span className="block">{t("hero.lineOne")}</span>
                  <span className="block text-dim">{t("hero.lineTwo")}</span>
                </h1>
                <p className="prose-width text-dim">{t("hero.body")}</p>
              </div>
              <div className="flex flex-wrap items-center gap-x-6 gap-y-3 lg:pb-1">
                <Link href="/register" className={buttonClass("primary")}>
                  {t("hero.create")}
                </Link>
                <Link href="/resources" className={buttonClass("quiet")}>
                  {t("hero.helplines")}
                </Link>
              </div>
            </div>
            <div className="border-t border-line">
              <p className="label mx-auto max-w-7xl px-5 py-4 text-dim lg:px-10">
                {t("hero.limits")}
              </p>
            </div>
          </div>
        </section>

        <section aria-labelledby="story-title" className="mx-auto max-w-7xl px-5 lg:px-10">
          <h2 id="story-title" className="sr-only">
            {t("story.title")}
          </h2>
          <Story steps={steps} />
        </section>

        <section className="mx-auto max-w-7xl px-5 py-24 lg:px-10">
          <div className="grid border border-line md:grid-cols-2">
            {(["is", "isNot"] as const).map((column) => (
              <div
                key={column}
                className="border-line p-6 max-md:[&+div]:border-t md:p-12 md:[&+div]:border-l"
              >
                <h2 className="label mb-8 text-moon">{t(`${column}.title`)}</h2>
                <ul>
                  {ITEMS.map((item) => (
                    <li
                      key={item}
                      className="border-t border-line py-4 text-dim first:border-t-0 first:pt-0"
                    >
                      {t(`${column}.items.${item}`)}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <HelplineStrip />
      </main>

      <footer>
        <Scene scene="terrain" label={t("footer.scene")} className="h-56 sm:h-72" />
        <div className="mx-auto max-w-7xl px-5 pb-12 lg:px-10">
          <div className="grid gap-8 pb-16 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
            <p className="footer-title max-w-3xl">
              <span>{t("footer.lineOne")} </span>
              <span className="text-dim">{t("footer.lineTwo")}</span>
            </p>
            <Link href="/register" className={buttonClass("primary")}>
              {t("hero.create")}
            </Link>
          </div>
          <div className="grid gap-10 border-t border-line pt-10 sm:grid-cols-3">
            <nav aria-label={t("footer.explore")}>
              <h2 className="label mb-3 text-dim">{t("footer.explore")}</h2>
              <ul>
                <li>
                  <Link href="/resources" className="footer-link">
                    {t("nav.helplines")}
                  </Link>
                </li>
                <li>
                  <Link href="/support" className="footer-link">
                    {t("footer.support")}
                  </Link>
                </li>
              </ul>
            </nav>
            <nav aria-label={t("footer.account")}>
              <h2 className="label mb-3 text-dim">{t("footer.account")}</h2>
              <ul>
                <li>
                  <Link href="/login" className="footer-link">
                    {t("nav.signIn")}
                  </Link>
                </li>
                <li>
                  <Link href="/register" className="footer-link">
                    {t("hero.create")}
                  </Link>
                </li>
              </ul>
            </nav>
            <div>
              <h2 className="label mb-3 text-dim">{t("footer.limits")}</h2>
              <ul className="space-y-2 text-sm">
                <li>{t("footer.limitA")}</li>
                <li>{t("footer.limitB")}</li>
                <li>{t("footer.limitC")}</li>
              </ul>
            </div>
          </div>
          <p className="label mt-12 border-t border-line pt-6 text-dim">{t("footer.prototype")}</p>
        </div>
      </footer>
    </>
  );
}
