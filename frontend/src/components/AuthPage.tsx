import type { ReactNode } from "react";

import { FormMascot } from "@/components/pet/Mascot";
import { PublicHeader } from "@/components/PublicHeader";

/** Shared frame for the signed-out forms: one glass card, centred on the aurora. */
export function AuthPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <>
      <PublicHeader />
      <div className="flex min-h-[calc(100svh-5rem)] items-center justify-center px-4 pb-10 pt-24">
        <main id="main" className="page-fade frame relative w-full max-w-md p-6 sm:p-8">
          {/* Sushi keeping the form company, perched on the card's top edge. */}
          <FormMascot className="absolute -top-14 right-6 w-24" />
          <h1 className="h1 mb-6">{title}</h1>
          {children}
        </main>
      </div>
    </>
  );
}
