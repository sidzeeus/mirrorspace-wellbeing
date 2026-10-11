"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { AuthPage } from "@/components/AuthPage";
import { Button, Field, Notice } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { useErrorText } from "@/lib/hooks";

export default function ForgotPasswordPage() {
  const t = useTranslations("auth");
  const errorText = useErrorText();
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "busy" | "sent">("idle");
  const [problem, setProblem] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!/^\S+@\S+\.\S+$/.test(email)) {
      setProblem(t("validation.email"));
      return;
    }
    setProblem(null);
    setState("busy");
    try {
      await api("/auth/password-reset", { method: "POST", body: { email } });
      setState("sent");
    } catch (error) {
      setProblem(errorText(error));
      setState("idle");
    }
  };

  return (
    <AuthPage title={t("forgot.title")}>
      {state === "sent" ? (
        <Notice tone="saved" role="status">
          {t("forgot.sent")}
        </Notice>
      ) : (
        <form onSubmit={submit} noValidate className="space-y-5">
          <p className="text-dim">{t("forgot.intro")}</p>
          <Field
            label={t("email")}
            name="email"
            type="email"
            autoComplete="email"
            inputMode="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            error={problem ?? undefined}
          />
          <Button type="submit" busy={state === "busy"} className="w-full">
            {t("forgot.submit")}
          </Button>
        </form>
      )}
      <p className="mt-6">
        <Link href="/login" className="link inline-flex min-h-11 items-center">
          {t("forgot.back")}
        </Link>
      </p>
    </AuthPage>
  );
}
