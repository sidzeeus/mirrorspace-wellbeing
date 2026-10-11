"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { AuthPage } from "@/components/AuthPage";
import { Button, Field, Notice } from "@/components/ui/primitives";
import { ApiError, api } from "@/lib/api";
import { useFragment } from "@/lib/fragment";
import { useErrorText } from "@/lib/hooks";

export default function ResetPasswordPage() {
  const t = useTranslations("auth");
  const errorText = useErrorText();
  const fragment = useFragment();
  const uid = fragment?.get("uid");
  const token = fragment?.get("token");
  const [password, setPassword] = useState("");
  const [state, setState] = useState<"idle" | "busy" | "done">("idle");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setFieldError(null);
    setProblem(null);
    if (password.length < 10) {
      setFieldError(t("validation.passwordLength"));
      return;
    }
    setState("busy");
    try {
      await api("/auth/password-reset/confirm", {
        method: "POST",
        body: { uid, token, new_password: password },
      });
      setState("done");
    } catch (error) {
      setState("idle");
      const message = error instanceof ApiError ? error.field("new_password") : undefined;
      if (message) setFieldError(message);
      else setProblem(errorText(error));
    }
  };

  const missing = fragment !== null && (!uid || !token);
  return (
    <AuthPage title={t("reset.title")}>
      {state === "done" ? (
        <>
          <Notice tone="saved" role="status">
            {t("reset.done")}
          </Notice>
          <p className="mt-6">
            <Link href="/login" className="btn btn-primary">
              {t("verify.signIn")}
            </Link>
          </p>
        </>
      ) : missing ? (
        <>
          <Notice tone="attention" role="alert">
            {t("reset.missing")}
          </Notice>
          <p className="mt-6">
            <Link href="/forgot-password" className="btn btn-quiet">
              {t("reset.request")}
            </Link>
          </p>
        </>
      ) : (
        <form onSubmit={submit} noValidate className="space-y-5">
          <Field
            label={t("reset.newPassword")}
            name="new_password"
            type="password"
            autoComplete="new-password"
            hint={t("register.passwordHint")}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            error={fieldError ?? undefined}
          />
          {problem ? (
            <Notice tone="attention" role="alert">
              <p>{problem}</p>
              <Link href="/forgot-password" className="link inline-flex min-h-11 items-center">
                {t("reset.request")}
              </Link>
            </Notice>
          ) : null}
          <Button type="submit" busy={state === "busy"} className="w-full">
            {t("reset.submit")}
          </Button>
        </form>
      )}
    </AuthPage>
  );
}
