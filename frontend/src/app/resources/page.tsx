import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { BackButton } from "@/components/BackButton";
import { PublicHeader } from "@/components/PublicHeader";
import { ResourceList } from "@/components/ResourceList";
import { Notice } from "@/components/ui/primitives";
import { type Resource, page, resourceSchema } from "@/lib/schemas";

const API = (process.env.API_INTERNAL_URL ?? "http://localhost:8000").replace(/\/$/, "");

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("resources"))("title") };
}

async function loadResources(): Promise<Resource[] | null> {
  try {
    const response = await fetch(`${API}/api/v1/resources?page_size=100`, {
      signal: AbortSignal.timeout(3000),
      next: { revalidate: 300 },
    });
    if (!response.ok) return null;
    return page(resourceSchema).parse(await response.json()).results;
  } catch {
    return null;
  }
}

/**
 * Public and rendered on the server, so it works before sign-up and without
 * JavaScript. The service worker keeps the last copy for offline use.
 */
export default async function ResourcesPage() {
  const [t, resources] = await Promise.all([getTranslations("resources"), loadResources()]);
  return (
    <>
      <PublicHeader />
      <main id="main" className="mx-auto max-w-3xl px-5 py-10">
        <BackButton className="mb-6" />
        <h1 className="h1 mb-4">{t("title")}</h1>
        <p className="prose-width mb-4 text-dim">{t("intro")}</p>
        <div className="mb-8">
          <Notice tone="attention">{t("emergency")}</Notice>
        </div>
        {resources === null ? (
          <Notice tone="attention" role="alert">
            {t("unavailable")}
          </Notice>
        ) : resources.length === 0 ? (
          <p className="prose-width text-dim">{t("empty")}</p>
        ) : (
          <ResourceList resources={resources} />
        )}
      </main>
    </>
  );
}
