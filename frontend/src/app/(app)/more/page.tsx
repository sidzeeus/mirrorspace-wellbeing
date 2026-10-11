"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/primitives";
import { api, forgetCsrfToken } from "@/lib/api";
import { useMe } from "@/lib/hooks";
import { clearOfflineCopies } from "@/lib/offline";

const LINKS = [
  { key: "patterns", href: "/patterns" },
  { key: "episodes", href: "/episodes" },
  { key: "sharing", href: "/sharing" },
  { key: "chat", href: "/chat" },
  { key: "resources", href: "/resources" },
  { key: "settings", href: "/settings" },
] as const;

export default function MorePage() {
  const t = useTranslations("shell.more_page");
  const me = useMe();
  const queryClient = useQueryClient();
  const signOut = useMutation({
    mutationFn: () => api("/auth/logout", { method: "POST" }),
    onSettled: () => {
      // Leave nothing of this person's on a shared device.
      clearOfflineCopies();
      forgetCsrfToken();
      queryClient.clear();
      // A full page load, on purpose: it drops everything held in memory.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign("/");
    },
  });

  return (
    <div>
      <h1 className="h1 mb-8">{t("title")}</h1>
      <ul className="frame mb-8 divide-y divide-line">
        {LINKS.map((link) => (
          <li key={link.key}>
            <Link href={link.href} className="block px-5 py-4 hover:bg-raised">
              <span className="block font-medium">{t(link.key)}</span>
              <span className="block text-sm text-dim">{t(`${link.key}Hint`)}</span>
            </Link>
          </li>
        ))}
      </ul>
      {me.data ? <p className="mb-3 text-sm text-dim">{t("signedInAs", { email: me.data.email })}</p> : null}
      <Button variant="quiet" busy={signOut.isPending} onClick={() => signOut.mutate()}>
        {t("signOut")}
      </Button>
    </div>
  );
}
