"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useId } from "react";

import { Toggle } from "@/components/ui/controls";
import { api } from "@/lib/api";
import { keys } from "@/lib/hooks";
import { type Theme, setPrefs, usePrefs } from "@/lib/prefs";

const LOCALES = ["en", "hi"] as const;
const THEMES: readonly Theme[] = ["system", "night", "daybreak"];

/**
 * Theme, text size, motion, data use and language. The first four stay on this
 * device. Language is also saved to the account so emails and content match.
 */
export function PreferenceControls() {
  const t = useTranslations("settings");
  const prefs = usePrefs();
  const locale = useLocale();
  const router = useRouter();
  const queryClient = useQueryClient();
  const themeId = useId();
  const languageId = useId();

  const language = useMutation({
    mutationFn: async (next: string) => {
      document.cookie = `locale=${next}; path=/; max-age=31536000; samesite=lax`;
      await api("/auth/me", { method: "PATCH", body: { preferred_language: next } }).catch(
        () => undefined,
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.me });
      void queryClient.invalidateQueries({ queryKey: ["exercises"] });
      router.refresh();
    },
  });

  return (
    <div className="space-y-5">
      <div>
        <label htmlFor={themeId} className="mb-1.5 block font-medium">
          {t("theme")}
        </label>
        <select
          id={themeId}
          className="control"
          value={prefs.theme}
          onChange={(event) => setPrefs({ theme: event.target.value as Theme })}
        >
          {THEMES.map((theme) => (
            <option key={theme} value={theme}>
              {t(`themes.${theme}`)}
            </option>
          ))}
        </select>
      </div>
      <Toggle
        label={t("largeText")}
        hint={t("largeTextHint")}
        checked={prefs.text === "large"}
        onChange={(checked) => setPrefs({ text: checked ? "large" : "normal" })}
      />
      <Toggle
        label={t("reducedMotion")}
        hint={t("reducedMotionHint")}
        checked={prefs.motion === "reduced"}
        onChange={(checked) => setPrefs({ motion: checked ? "reduced" : "system" })}
      />
      <Toggle
        label={t("lowBandwidth")}
        hint={t("lowBandwidthHint")}
        checked={prefs.bandwidth === "low"}
        onChange={(checked) => setPrefs({ bandwidth: checked ? "low" : "auto" })}
      />
      <p className="text-sm text-dim">{t("deviceNote")}</p>
      <div>
        <label htmlFor={languageId} className="mb-1.5 block font-medium">
          {t("language")}
        </label>
        <p className="mb-1.5 text-sm text-dim">{t("languageHint")}</p>
        <select
          id={languageId}
          className="control"
          value={locale}
          onChange={(event) => language.mutate(event.target.value)}
        >
          {LOCALES.map((code) => (
            <option key={code} value={code} lang={code}>
              {t(`languages.${code}`)}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
