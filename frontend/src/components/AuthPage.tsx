import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { PublicHeader } from "@/components/PublicHeader";
import { Scene } from "@/components/scene/Scene";

/** Shared frame for the signed-out forms: the form, and on wide screens a picture. */
export function AuthPage({ title, children }: { title: string; children: ReactNode }) {
  const t = useTranslations("landing.story.two");
  return (
    <>
      <PublicHeader />
      <div className="mx-auto grid max-w-7xl lg:min-h-[calc(100svh-4rem)] lg:grid-cols-2">
        <main id="main" className="page-fade mx-auto w-full max-w-md px-5 py-12 lg:self-center">
          <h1 className="h1 mb-6">{title}</h1>
          {children}
        </main>
        <div className="hidden border-l border-line lg:block">
          <Scene scene="figure" label={t("lumen")} className="h-full" />
        </div>
      </div>
    </>
  );
}
