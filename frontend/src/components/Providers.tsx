"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { type ReactNode, useState } from "react";

import { ServiceWorker } from "@/components/ServiceWorker";
import { ToastProvider } from "@/components/ui/controls";

export function Providers({ children }: { children: ReactNode }) {
  const t = useTranslations("common");
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
          mutations: { retry: 0 },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <ToastProvider closeLabel={t("close")}>
        <ServiceWorker />
        {children}
      </ToastProvider>
    </QueryClientProvider>
  );
}
