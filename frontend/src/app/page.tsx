import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { HelplineStrip } from "@/components/landing/HelplineStrip";
import { Story } from "@/components/landing/Story";
import { Lumen } from "@/components/lumen/Lumen";
import { PublicHeader } from "@/components/PublicHeader";
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
        <section className="mx-auto grid max-w-6xl gap-10 px-5 pb-20 pt-10 lg:grid-cols-[minmax(0,6fr)_minmax(0,5fr)] lg:items-center lg:gap-16 lg:pb-28 lg:pt-20">
          <div className="marks order-first mx-auto w-full max-w-[19rem] border border-line lg:order-last lg:max-w-md">
            {/* The landing page's one moment: the light gathers from scattered points. */}
            <Lumen
              label={t("hero.lumen")}
              mode="orb"
              assemble
              intensity={0.9}
              density={1}
              hue={0.35}
            />
          </div>
          <div>
            <h1 className="display mb-6">
              <span className="block">{t("hero.lineOne")}</span>
              <span className="block text-dim">{t("hero.lineTwo")}</span>
            </h1>
            <p className="prose-width mb-8 text-lg text-dim">{t("hero.body")}</p>
            <div className="mb-6 flex flex-wrap items-center gap-x-6 gap-y-3">
              <Link href="/register" className={buttonClass("primary")}>
                {t("hero.create")}
              </Link>
              <Link href="/resources" className="btn-text inline-flex items-center">
                {t("hero.helplines")}
              </Link>
            </div>
            <p className="text-sm text-dim">{t("hero.limits")}</p>
          </div>
        </section>

        <section aria-labelledby="story-title" className="mx-auto max-w-6xl px-5 pb-10">
          <h2 id="story-title" className="sr-only">
            {t("story.title")}
          </h2>
          <Story steps={steps} />
        </section>

        <section className="mx-auto max-w-6xl px-5 py-20">
          <div className="grid border border-line md:grid-cols-2">
            {(["is", "isNot"] as const).map((column) => (
              <div
                key={column}
                className="border-line p-6 max-md:[&+div]:border-t md:p-10 md:[&+div]:border-l"
              >
                <h2 className="h2 mb-6">{t(`${column}.title`)}</h2>
                <ul className="space-y-4">
                  {ITEMS.map((item) => (
                    <li
                      key={item}
                      className="border-t border-line pt-4 text-dim first:border-t-0 first:pt-0"
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

      <footer className="mx-auto max-w-6xl px-5 py-20">
        <p className="h1 mb-10 max-w-3xl">
          <span>{t("footer.lineOne")} </span>
          <span className="text-dim">{t("footer.lineTwo")}</span>
        </p>
        <nav aria-label={t("footer.lineOne")} className="mb-8 flex flex-wrap gap-x-6 gap-y-1">
          <Link href="/resources" className="btn-text inline-flex items-center">
            {t("nav.helplines")}
          </Link>
          <Link href="/login" className="btn-text inline-flex items-center">
            {t("nav.signIn")}
          </Link>
          <Link href="/register" className="btn-text inline-flex items-center">
            {t("hero.create")}
          </Link>
        </nav>
        <p className="prose-width text-sm text-dim">{t("footer.prototype")}</p>
      </footer>
    </>
  );
}
