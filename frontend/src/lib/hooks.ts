"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useCallback } from "react";

import { ApiError, api } from "./api";
import {
  consentSchema,
  exerciseSchema,
  meSchema,
  noticesSchema,
  page,
  resourceSchema,
  safetyPlanSchema,
} from "./schemas";

export const keys = {
  me: ["me"] as const,
  consents: ["consents"] as const,
  notices: ["notices"] as const,
  checkIns: (from: string) => ["check-ins", from] as const,
  patterns: (days: number) => ["patterns", days] as const,
  exercises: (hidden: boolean) => ["exercises", hidden] as const,
  triggers: ["triggers"] as const,
  episodes: ["episodes"] as const,
  plan: ["safety-plan"] as const,
  resources: ["resources"] as const,
  contacts: ["contacts"] as const,
  notifications: ["notifications"] as const,
};

/** The signed-in person, or null when nobody is signed in. */
export function useMe() {
  return useQuery({
    queryKey: keys.me,
    queryFn: async () => {
      try {
        return await api("/auth/me", { schema: meSchema });
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
    staleTime: 60_000,
  });
}

export function useConsents(enabled = true) {
  return useQuery({
    queryKey: keys.consents,
    queryFn: () => api("/sharing/consent?page_size=100", { schema: page(consentSchema) }),
    enabled,
  });
}

export function useNotices(enabled = true) {
  return useQuery({
    queryKey: keys.notices,
    queryFn: () => api("/sharing/notices", { schema: noticesSchema }),
    staleTime: 300_000,
    enabled,
  });
}

export function useExercises(includeHidden = false) {
  return useQuery({
    queryKey: keys.exercises(includeHidden),
    queryFn: () =>
      api(`/exercises?page_size=100${includeHidden ? "&include_hidden=true" : ""}`, {
        schema: page(exerciseSchema),
      }),
  });
}

export function useResources() {
  return useQuery({
    queryKey: keys.resources,
    queryFn: () => api("/resources?page_size=100", { schema: page(resourceSchema) }),
  });
}

export function useSafetyPlan(enabled = true) {
  return useQuery({
    queryKey: keys.plan,
    queryFn: () => api("/safety-plan", { schema: safetyPlanSchema }),
    enabled,
  });
}

/**
 * Turns any failure into one sentence that says what happened and what to do.
 * The API's own message is used when it gave one.
 */
export function useErrorText() {
  const t = useTranslations("common.errors");
  return useCallback(
    (error: unknown): string => {
      if (error instanceof ApiError) {
        if (error.status === 0) return t("offline");
        if (error.status === 429) return t("throttled");
        if (error.status === 401) return t("session");
        if (error.status === 503) return t("unreachable");
        if (error.detail) return error.detail;
      }
      return t("generic");
    },
    [t],
  );
}

/** Today's date (YYYY-MM-DD) in a given time zone. */
export function localDate(timeZone: string, offsetDays = 0): string {
  const moment = new Date(Date.now() + offsetDays * 86_400_000);
  try {
    return new Intl.DateTimeFormat("en-CA", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(moment);
  } catch {
    return moment.toISOString().slice(0, 10);
  }
}

export function browserTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Kolkata";
  } catch {
    return "Asia/Kolkata";
  }
}
