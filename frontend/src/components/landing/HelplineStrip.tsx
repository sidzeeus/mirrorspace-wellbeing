import Link from "next/link";
import { getFormatter, getTranslations } from "next-intl/server";

import { UnreviewedBadge } from "@/components/ui/primitives";

type Resource = {
  id: string;
  name: string;
  phone: string;
  region: string;
  verified_on: string | null;
  stale: boolean;
  reviewed: boolean;
};

const API = (process.env.API_INTERNAL_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function loadResources(): Promise<Resource[] | null> {
  try {
    const response = await fetch(`${API}/api/v1/resources?page_size=4`, {
      signal: AbortSignal.timeout(1500),
      next: { revalidate: 300 },
    });
    if (!response.ok) return null;
    return ((await response.json()) as { results: Resource[] }).results;
  } catch {
    return null;
  }
}

/** Helplines, visible before sign-up. Shows only what the API says a person verified. */
export async function HelplineStrip() {
  const [t, common, format, resources] = await Promise.all([
    getTranslations("landing.helplines"),
    getTranslations("common"),
    getFormatter(),
    loadResources(),
  ]);
  const withPhone = (resources ?? []).filter((resource) => resource.phone);
  return (
    <section aria-labelledby="helplines-title" className="mx-auto max-w-6xl px-5 pb-20">
      <div className="frame p-6 md:p-9">
        <div className="mb-8 flex flex-wrap items-baseline justify-between gap-4">
          <h2 id="helplines-title" className="h2">
            {t("title")}
          </h2>
          <Link href="/resources" className="link inline-flex min-h-11 items-center">
            {t("all")}
          </Link>
        </div>
        {withPhone.length > 0 ? (
          <>
            <ul className="grid gap-3 sm:grid-cols-2">
              {withPhone.map((resource) => (
                <li key={resource.id} className="rounded-2xl border border-line p-5">
                  <p className="mb-1 flex flex-wrap items-center gap-2 font-medium">
                    {resource.name}
                    {resource.reviewed ? null : (
                      <UnreviewedBadge>{common("unverified")}</UnreviewedBadge>
                    )}
                  </p>
                  <a
                    href={`tel:${resource.phone.replace(/\s+/g, "")}`}
                    aria-label={t("call", { name: resource.name, phone: resource.phone })}
                    className="data link inline-flex min-h-11 items-center text-2xl"
                  >
                    {resource.phone}
                  </a>
                  <p className="data text-dim">
                    {resource.region} ·{" "}
                    {resource.verified_on
                      ? t("verified", {
                          date: format.dateTime(new Date(resource.verified_on), {
                            dateStyle: "medium",
                          }),
                        })
                      : t("never")}
                  </p>
                </li>
              ))}
            </ul>
            <p className="mt-4 text-sm text-dim">{t("note")}</p>
          </>
        ) : (
          <p className="prose-width text-dim">
            {resources === null ? t("unavailable") : t("empty")}
          </p>
        )}
      </div>
    </section>
  );
}
