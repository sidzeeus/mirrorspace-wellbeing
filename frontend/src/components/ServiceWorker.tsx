"use client";

import { useTranslations } from "next-intl";
import { useEffect } from "react";

import { useToast } from "@/components/ui/controls";

/**
 * Registers the service worker (production builds only; in development it removes any
 * left behind) and handles updates: when a new version is waiting, the person is told
 * and chooses when to reload. Nothing is swapped underneath them mid-task.
 */
export function ServiceWorker() {
  const t = useTranslations("common.update");
  const toast = useToast();

  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    if (process.env.NODE_ENV !== "production") {
      // A production build served from this same address may have left a worker
      // behind. In development it would keep serving stale scripts and styles, because
      // development file names do not change when their content does. Remove it.
      void navigator.serviceWorker.getRegistrations().then(async (registrations) => {
        if (registrations.length === 0) return;
        await Promise.all(registrations.map((registration) => registration.unregister()));
        await Promise.all((await caches.keys()).map((name) => caches.delete(name)));
        window.location.reload();
      });
      return;
    }
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
