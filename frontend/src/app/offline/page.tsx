import { getTranslations } from "next-intl/server";

import { buttonClass } from "@/components/ui/primitives";

/** Shown by the service worker when a page that was never saved is opened offline. */
export default async function OfflinePage() {
  const t = await getTranslations("offline");
  return (
    <main id="main" className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-5 py-12">
      <h1 className="h1 mb-4">{t("title")}</h1>
      <p className="mb-8 text-dim">{t("body")}</p>
      <div className="flex flex-col gap-3">
        <a href="/support" className={buttonClass("care")}>
          {t("support")}
        </a>
        <a href="/resources" className={buttonClass("quiet")}>
          {t("helplines")}
        </a>
        <a href="/home" className={buttonClass("quiet")}>
          {t("retry")}
        </a>
      </div>
    </main>
  );
}
