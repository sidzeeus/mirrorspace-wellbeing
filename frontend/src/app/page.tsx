import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { HelplineStrip } from "@/components/landing/HelplineStrip";
import { Story } from "@/components/landing/Story";
import { Pet } from "@/components/pet/Pet";
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
        {/* The stage: one gathering light, and the promise beneath it. */}
        <section className="mx-auto flex min-h-[calc(100svh-6rem)] max-w-4xl flex-col items-center justify-center px-5 pb-16 pt-4 text-center">
          <Pet label={t("hero.lumen")} species="cat" className="mb-2 w-36 sm:w-44" />
          <p className="pill mb-5 text-dim">{t("hero.eyebrow")}</p>
          <h1 className="display mb-6">
            <span className="block">{t("hero.lineOne")}</span>
            <span className="block text-dim">{t("hero.lineTwo")}</span>
          </h1>
          <p className="prose-width mx-auto mb-8 text-lg text-dim">{t("hero.body")}</p>
          <div className="mb-8 flex flex-wrap items-center justify-center gap-3">
            <Link href="/register" className={buttonClass("primary")}>
              {t("hero.create")}
            </Link>
            <Link href="/resources" className={buttonClass("quiet")}>
              {t("hero.helplines")}
            </Link>
          </div>
          <p className="text-sm text-dim">{t("hero.limits")}</p>
        </section>

        <section aria-labelledby="story-title" className="mx-auto max-w-6xl px-5 pb-20">
          <h2 id="story-title" className="label mb-6 text-center text-dim">
            {t("story.title")}
          </h2>
          <Story steps={steps} />
        </section>

        <section className="mx-auto grid max-w-6xl gap-5 px-5 pb-20 md:grid-cols-2">
          {(["is", "isNot"] as const).map((column) => (
            <div key={column} className="frame p-6 md:p-9">
              <h2 className="h2 mb-6">{t(`${column}.title`)}</h2>
              <ul>
                {ITEMS.map((item) => (
                  <li
                    key={item}
                    className="border-t border-line py-4 text-dim first:border-t-0 first:pt-0 last:pb-0"
                  >
                    {t(`${column}.items.${item}`)}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </section>

        <HelplineStrip />
      </main>

      <footer className="mx-auto max-w-6xl px-5 pb-10">
        <div className="frame p-6 md:p-10">
          <div className="mb-10 flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <p className="h1 max-w-2xl">
              <span>{t("footer.lineOne")} </span>
              <span className="text-dim">{t("footer.lineTwo")}</span>
            </p>
            <Link href="/register" className={`${buttonClass("primary")} self-start md:self-auto`}>
              {t("hero.create")}
            </Link>
          </div>
          <div className="grid gap-8 border-t border-line pt-8 sm:grid-cols-3">
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
          <p className="mt-8 border-t border-line pt-6 text-sm text-dim">{t("footer.prototype")}</p>
        </div>
      </footer>
    </>
  );
}
