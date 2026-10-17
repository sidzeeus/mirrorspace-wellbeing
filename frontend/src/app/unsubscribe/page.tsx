"use client";

import { useMutation } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { AuthPage } from "@/components/AuthPage";
import { Button, Notice } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { useFragment } from "@/lib/fragment";

/** Opened from the link in any email to a trusted contact. One press, no account. */
export default function UnsubscribePage() {
  const t = useTranslations("contact.unsubscribe");
  const fragment = useFragment();
  const token = fragment?.get("token") ?? null;
  const [blockAll, setBlockAll] = useState(false);
  const unsubscribe = useMutation({
    mutationFn: () => api("/unsubscribe", { method: "POST", body: { token, block_all: blockAll } }),
  });

  return (
    <AuthPage title={t("title")}>
      {fragment !== null && !token ? (
        <Notice tone="attention" role="alert">
          {t("missing")}
        </Notice>
      ) : unsubscribe.isSuccess ? (
        <Notice tone="saved" role="status">
          {t("done")}
        </Notice>
      ) : (
        <div className="space-y-5">
          <p className="text-dim">{t("body")}</p>
          <label className="flex min-h-11 cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              className="mt-1 h-6 w-6 shrink-0 accent-(--accent-hi)"
              checked={blockAll}
              onChange={(event) => setBlockAll(event.target.checked)}
            />
            <span>{t("blockAll")}</span>
          </label>
          {unsubscribe.isError ? (
            <Notice tone="attention" role="alert">
              {t("invalid")}
            </Notice>
          ) : null}
          <Button busy={unsubscribe.isPending} disabled={!token} onClick={() => unsubscribe.mutate()}>
            {t("submit")}
          </Button>
        </div>
      )}
    </AuthPage>
  );
}
