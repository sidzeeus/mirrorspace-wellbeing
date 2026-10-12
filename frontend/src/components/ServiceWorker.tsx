"use client";

import { useTranslations } from "next-intl";
import { useEffect } from "react";

import { useToast } from "@/components/ui/controls";

/**
 * Registers the service worker (production builds only) and handles updates: when a
 * new version is waiting, the person is told and chooses when to reload. Nothing is
 * swapped underneath them mid-task.
 */
export function ServiceWorker() {
  const t = useTranslations("common.update");
  const toast = useToast();

  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;
    let reloading = false;
    const onControllerChange = () => {
      if (reloading) window.location.reload();
    };
    const offer = (worker: ServiceWorker) =>
      toast(t("available"), {
        label: t("reload"),
        run: () => {
          reloading = true;
          worker.postMessage("skip-waiting");
        },
      });

    navigator.serviceWorker.addEventListener("controllerchange", onControllerChange);
    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .then((registration) => {
        if (registration.waiting && navigator.serviceWorker.controller) offer(registration.waiting);
        registration.addEventListener("updatefound", () => {
          const incoming = registration.installing;
          incoming?.addEventListener("statechange", () => {
            if (incoming.state === "installed" && navigator.serviceWorker.controller) offer(incoming);
          });
        });
      })
      .catch(() => undefined);
    return () =>
      navigator.serviceWorker.removeEventListener("controllerchange", onControllerChange);
  }, [t, toast]);

  return null;
}
