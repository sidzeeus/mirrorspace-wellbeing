"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect } from "react";

import { AuthPage } from "@/components/AuthPage";
import { Notice } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { useFragment } from "@/lib/fragment";

export default function VerifyEmailPage() {
  const t = useTranslations("auth.verify");
  const fragment = useFragment();
  const token = fragment?.get("token") ?? null;
  const { mutate, status } = useMutation({
    mutationFn: (value: string) =>
      api("/auth/verify-email", { method: "POST", body: { token: value } }),
  });

  useEffect(() => {
    if (token) mutate(token);
  }, [token, mutate]);

  const state = fragment === null ? "working" : !token ? "missing" : status;
  return (
    <AuthPage title={t("title")}>
      {state === "success" ? (
        <Notice tone="saved" role="status">
          {t("done")}
        </Notice>
      ) : state === "error" ? (
        <Notice tone="attention" role="alert">
          {t("failed")}
        </Notice>
      ) : state === "missing" ? (
        <Notice tone="attention" role="alert">
          {t("missing")}
        </Notice>
      ) : (
        <p role="status">{t("working")}</p>
      )}
      <p className="mt-6">
        <Link href="/login" className="btn btn-quiet">
          {t("signIn")}
        </Link>
      </p>
    </AuthPage>
  );
}
