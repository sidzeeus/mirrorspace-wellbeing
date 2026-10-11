"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthPage } from "@/components/AuthPage";
import { Button, Field, Notice } from "@/components/ui/primitives";
import { ApiError, api, forgetCsrfToken } from "@/lib/api";
import { keys, useErrorText } from "@/lib/hooks";
import { meSchema } from "@/lib/schemas";

export default function LoginPage() {
  const t = useTranslations("auth");
  const errorText = useErrorText();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [problem, setProblem] = useState<string | null>(null);
  const [unverified, setUnverified] = useState(false);
  const [resent, setResent] = useState(false);

  const schema = z.object({
    email: z.email(t("validation.email")),
    password: z.string().min(1, t("validation.password")),
  });
  const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });
  const { errors, isSubmitting } = form.formState;

  const submit = form.handleSubmit(async (values) => {
    setProblem(null);
    setUnverified(false);
    setResent(false);
    try {
      const me = await api("/auth/login", { method: "POST", body: values, schema: meSchema });
      forgetCsrfToken();
      queryClient.clear();
      queryClient.setQueryData(keys.me, me);
      router.replace("/home");
    } catch (error) {
      if (error instanceof ApiError && error.code === "email_not_verified") setUnverified(true);
      else setProblem(errorText(error));
    }
  });

  const resend = async () => {
    try {
      await api("/auth/resend-verification", {
        method: "POST",
        body: { email: form.getValues("email") },
      });
      setResent(true);
    } catch (error) {
      setProblem(errorText(error));
    }
  };

  return (
    <AuthPage title={t("login.title")}>
      <form onSubmit={submit} noValidate className="space-y-5">
        <Field
          label={t("email")}
          type="email"
          autoComplete="email"
          inputMode="email"
          error={errors.email?.message}
          {...form.register("email")}
        />
        <Field
          label={t("password")}
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...form.register("password")}
        />
        {problem ? (
          <Notice tone="attention" role="alert">
            {problem}
          </Notice>
        ) : null}
        {unverified ? (
          <Notice tone="attention" role="alert">
            <p className="mb-2">{t("login.notVerified")}</p>
            {resent ? (
              <p>{t("login.resent")}</p>
            ) : (
              <Button variant="quiet" onClick={resend}>
                {t("login.resend")}
              </Button>
            )}
          </Notice>
        ) : null}
        <Button type="submit" busy={isSubmitting} className="w-full">
          {t("login.submit")}
        </Button>
      </form>
      <p className="mt-6">
        <Link href="/forgot-password" className="link inline-flex min-h-11 items-center">
          {t("login.forgot")}
        </Link>
      </p>
      <p className="text-dim">
        {t("login.noAccount")}{" "}
        <Link href="/register" className="link inline-flex min-h-11 items-center">
          {t("login.create")}
        </Link>
      </p>
    </AuthPage>
  );
}
