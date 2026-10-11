"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthPage } from "@/components/AuthPage";
import { Button, Field, Notice } from "@/components/ui/primitives";
import { ApiError, api } from "@/lib/api";
import { browserTimeZone, useErrorText } from "@/lib/hooks";

export default function RegisterPage() {
  const t = useTranslations("auth");
  const locale = useLocale();
  const errorText = useErrorText();
  const [sent, setSent] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const schema = z.object({
    email: z.email(t("validation.email")),
    password: z.string().min(10, t("validation.passwordLength")),
    display_name: z.string().max(60).optional(),
    age_confirmed: z.boolean().refine((value) => value, t("register.ageRequired")),
  });
  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { age_confirmed: false },
  });
  const { errors, isSubmitting } = form.formState;

  const submit = form.handleSubmit(async (values) => {
    setProblem(null);
    try {
      await api("/auth/register", {
        method: "POST",
        body: {
          ...values,
          display_name: values.display_name?.trim() ?? "",
          preferred_language: locale,
          timezone: browserTimeZone(),
        },
      });
      setSent(true);
    } catch (error) {
      if (error instanceof ApiError && Object.keys(error.fields).length > 0) {
        for (const name of ["email", "password", "display_name", "age_confirmed"] as const) {
          const message = error.field(name);
          if (message) form.setError(name, { message });
        }
        const other = error.field("timezone") ?? error.field("preferred_language");
        if (other) setProblem(other);
      } else {
        setProblem(errorText(error));
      }
    }
  });

  if (sent) {
    return (
      <AuthPage title={t("register.sentTitle")}>
        <div role="status" className="space-y-4">
          <p>{t("register.sentBody")}</p>
          <p className="text-dim">{t("register.sentNote")}</p>
        </div>
        <p className="mt-6">
          <Link href="/login" className="btn btn-quiet">
            {t("verify.signIn")}
          </Link>
        </p>
      </AuthPage>
    );
  }

  return (
    <AuthPage title={t("register.title")}>
      <p className="mb-6 text-dim">{t("register.intro")}</p>
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
          autoComplete="new-password"
          hint={t("register.passwordHint")}
          error={errors.password?.message}
          {...form.register("password")}
        />
        <Field
          label={t("register.displayName")}
          autoComplete="nickname"
          hint={t("register.displayNameHint")}
          error={errors.display_name?.message}
          {...form.register("display_name")}
        />
        <div>
          <label className="flex min-h-11 cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              className="mt-1 h-6 w-6 shrink-0 accent-(--lumen-hi)"
              aria-describedby="age-hint"
              aria-invalid={errors.age_confirmed ? true : undefined}
              {...form.register("age_confirmed")}
            />
            <span>
              <span className="block font-medium">{t("register.age")}</span>
              <span id="age-hint" className="block text-sm text-dim">
                {t("register.ageHint")}
              </span>
            </span>
          </label>
          {errors.age_confirmed ? (
            <p role="alert" className="mt-1.5 text-sm text-warm">
              {errors.age_confirmed.message}
            </p>
          ) : null}
        </div>
        {problem ? (
          <Notice tone="attention" role="alert">
            {problem}
          </Notice>
        ) : null}
        <Button type="submit" busy={isSubmitting} className="w-full">
          {t("register.submit")}
        </Button>
      </form>
      <p className="mt-6 text-sm text-dim">{t("register.limits")}</p>
      <p className="text-dim">
        {t("register.haveAccount")}{" "}
        <Link href="/login" className="link inline-flex min-h-11 items-center">
          {t("login.submit")}
        </Link>
      </p>
    </AuthPage>
  );
}
