import { useFormatter, useTranslations } from "next-intl";

import { Notice, UnreviewedBadge } from "@/components/ui/primitives";
import type { Resource } from "@/lib/schemas";

/**
 * Helplines with region, language, type, the date they were last checked, and a
 * tap-to-call action. Stale entries are flagged in words, not only by color.
 * Works in server and client components.
 */
export function ResourceList({ resources }: { resources: readonly Resource[] }) {
  const t = useTranslations("resources");
  const common = useTranslations("common");
  const format = useFormatter();
  return (
    <ul className="space-y-4">
      {resources.map((resource) => (
        <li key={resource.id} className="frame p-5">
          <div className="mb-2 flex flex-wrap items-center gap-x-3 gap-y-1">
            <h2 className="h2">{resource.name}</h2>
            <span className="data text-dim">{t(`types.${resource.type}`)}</span>
            {resource.reviewed ? null : <UnreviewedBadge>{common("unverified")}</UnreviewedBadge>}
          </div>
          {resource.description ? <p className="mb-3 text-dim">{resource.description}</p> : null}
          <div className="mb-3 flex flex-wrap items-center gap-3">
            {resource.phone ? (
              <a
                href={`tel:${resource.phone.replace(/\s+/g, "")}`}
                aria-label={t("callLabel", { name: resource.name, phone: resource.phone })}
                className="btn btn-primary data text-lg"
              >
                {t("call", { phone: resource.phone })}
              </a>
            ) : null}
            {resource.url ? (
              <a
                href={resource.url}
                rel="noopener noreferrer"
                aria-label={t("website", { name: resource.name })}
                className="btn btn-quiet"
              >
                {t("websiteShort")}
              </a>
            ) : null}
          </div>
          <dl className="data grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-dim">
            <dt>{t("region")}</dt>
            <dd>{resource.region}</dd>
            {resource.languages.length > 0 ? (
              <>
                <dt>{t("languages")}</dt>
                <dd>{resource.languages.join(", ")}</dd>
              </>
            ) : null}
            {resource.hours ? (
              <>
                <dt>{t("hours")}</dt>
                <dd>{resource.hours}</dd>
              </>
            ) : null}
          </dl>
          <p className="data mt-3 text-dim">
            {resource.verified_on
              ? t("verified", {
                  date: format.dateTime(new Date(resource.verified_on), { dateStyle: "medium" }),
                })
              : t("never")}
          </p>
          {resource.stale ? (
            <div className="mt-3">
              <Notice tone="attention">{t("stale")}</Notice>
            </div>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
