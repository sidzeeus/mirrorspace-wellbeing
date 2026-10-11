"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { PreferenceControls } from "@/components/PreferenceControls";
import { Button, Notice } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { PRIVACY_PURPOSE } from "@/lib/constants";
import { keys, useErrorText, useNotices } from "@/lib/hooks";

const SECTIONS = ["what", "private", "control"] as const;

/**
 * Two short steps. The notice and the age confirmation cannot be skipped; the
 * preferences can. Accepting records a versioned consent on the server.
 */
export default function OnboardingPage() {
  const t = useTranslations("onboarding");
  const errorText = useErrorText();
  const router = useRouter();
  const queryClient = useQueryClient();
  const notices = useNotices();
  const [step, setStep] = useState<1 | 2>(1);
  const [age, setAge] = useState(false);
  const [read, setRead] = useState(false);
  const [missing, setMissing] = useState(false);

  const accept = useMutation({
    mutationFn: () =>
      api("/sharing/consent", {
        method: "POST",
        body: {
          purpose: PRIVACY_PURPOSE,
          notice_version: notices.data?.privacy_notice_version,
          confirmed: true,
        },
      }),
    onSuccess: () => setStep(2),
  });

  const finish = async () => {
    await queryClient.invalidateQueries({ queryKey: keys.consents });
    router.replace("/home");
  };

  return (
    <div className="mx-auto max-w-xl">
      <p className="data mb-4 text-dim" aria-live="polite">
        {t("progress", { step, total: 2 })}
      </p>
      {step === 1 ? (
        <>
          <h1 className="h1 mb-3">{t("notice.title")}</h1>
          <p className="mb-8 text-dim">{t("notice.intro")}</p>
          <div className="frame mb-8 divide-y divide-line">
            {SECTIONS.map((section) => (
              <section key={section} className="p-5">
                <h2 className="mb-1 font-medium">{t(`notice.${section}.title`)}</h2>
                <p className="text-dim">{t(`notice.${section}.body`)}</p>
              </section>
            ))}
          </div>
          <form
            noValidate
            onSubmit={(event) => {
              event.preventDefault();
              if (!age || !read) setMissing(true);
              else accept.mutate();
            }}
            className="space-y-3"
          >
            {(
              [
                ["age", age, setAge],
                ["read", read, setRead],
              ] as const
            ).map(([name, value, set]) => (
              <label key={name} className="flex min-h-11 cursor-pointer items-center gap-3">
                <input
                  type="checkbox"
                  className="h-6 w-6 shrink-0 accent-(--lumen-hi)"
                  checked={value}
                  onChange={(event) => {
                    set(event.target.checked);
                    setMissing(false);
                  }}
                />
                <span className="font-medium">{t(`notice.${name}`)}</span>
              </label>
            ))}
            {missing ? (
              <Notice tone="attention" role="alert">
                {t("notice.required")}
              </Notice>
            ) : null}
            {accept.isError ? (
              <Notice tone="attention" role="alert">
                {errorText(accept.error)}
              </Notice>
            ) : null}
            <p className="data text-dim">
              {t("notice.version", { version: notices.data?.privacy_notice_version ?? "…" })}
            </p>
            <Button type="submit" busy={accept.isPending} disabled={!notices.data}>
              {t("notice.continue")}
            </Button>
          </form>
        </>
      ) : (
        <>
          <h1 className="h1 mb-3">{t("preferences.title")}</h1>
          <p className="mb-8 text-dim">{t("preferences.intro")}</p>
          <PreferenceControls />
          <div className="mt-8 flex flex-wrap gap-3">
            <Button onClick={finish}>{t("preferences.finish")}</Button>
            <Button variant="quiet" onClick={finish}>
              {t("preferences.skip")}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
