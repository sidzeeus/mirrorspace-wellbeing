"use client";

import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";

import { Notice, buttonClass } from "@/components/ui/primitives";
import { useConsents, useErrorText } from "@/lib/hooks";

/** Every grant and withdrawal, with the notice version the person saw and when. */
export default function ConsentHistoryPage() {
  const t = useTranslations("sharing.history");
  const common = useTranslations("common");
  const format = useFormatter();
  const errorText = useErrorText();
  const consents = useConsents();
  const when = (iso: string) => format.dateTime(new Date(iso), { dateStyle: "medium", timeStyle: "short" });

  return (
    <div>
      <h1 className="h1 mb-3">{t("title")}</h1>
      <p className="prose-width mb-8 text-dim">{t("intro")}</p>
      {consents.isError ? (
        <Notice tone="attention" role="alert">
          {errorText(consents.error)}
        </Notice>
      ) : !consents.data ? (
        <p role="status" className="text-dim">
          {common("loading")}
        </p>
      ) : consents.data.results.length === 0 ? (
        <p className="text-dim">{t("empty")}</p>
      ) : (
        <ol className="frame divide-y divide-line">
          {consents.data.results.map((consent) => (
            <li key={consent.id} className="p-5" data-history={consent.status}>
              <p className="mb-1 flex flex-wrap items-center gap-3 font-medium">
                {t(`purpose.${consent.purpose}`)}
                <span className="data text-dim">{t(`status.${consent.status}`)}</span>
              </p>
              <p className="data text-dim">{t("granted", { date: when(consent.granted_at) })}</p>
              {consent.paused_at ? (
                <p className="data text-dim">{t("paused", { date: when(consent.paused_at) })}</p>
              ) : null}
              {consent.revoked_at ? (
                <p className="data text-dim">{t("revoked", { date: when(consent.revoked_at) })}</p>
              ) : null}
              <p className="data text-dim">{t("version", { version: consent.notice_version })}</p>
            </li>
          ))}
        </ol>
      )}
      <p className="mt-8">
        <Link href="/sharing" className={buttonClass("quiet")}>
          {t("back")}
        </Link>
      </p>
    </div>
  );
}
