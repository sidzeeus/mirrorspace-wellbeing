import type { ReactNode } from "react";

import { PublicHeader } from "@/components/PublicHeader";

/** Shared frame for the signed-out forms: one narrow column, one heading. */
export function AuthPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <>
      <PublicHeader />
      <main id="main" className="page-fade mx-auto w-full max-w-md px-5 py-12">
        <h1 className="h1 mb-6">{title}</h1>
        {children}
      </main>
    </>
  );
}
