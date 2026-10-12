"use client";

/**
 * Offline copies (decision D7).
 *
 * Kept on the device so Support works with no connection:
 *   - the person's own safety plan (private; removed on sign-out and account deletion)
 *   - the helpline list (public)
 *   - the exercise texts (public, shared content)
 * Nothing else is ever stored here: no check-ins, no episodes, no contacts, no chat.
 * A browser test enforces that list.
 */
import { useQuery } from "@tanstack/react-query";

import { api } from "./api";
import {
  type Exercise,
  type Resource,
  type SafetyPlan,
  exerciseSchema,
  page,
  resourceSchema,
  safetyPlanSchema,
} from "./schemas";

export const OFFLINE_KEYS = {
  plan: "offline.safetyPlan",
  resources: "offline.resources",
  exercises: "offline.exercises",
} as const;

/** Every key this app may write to localStorage. */
export const ALLOWED_STORAGE_KEYS = ["prefs", ...Object.values(OFFLINE_KEYS)] as const;

type Saved<T> = { savedAt: string; data: T };
/** Fresh from the server (`savedAt` null) or the copy on this device. */
export type OfflineResult<T> = { data: T; savedAt: string | null };

function write<T>(key: string, data: T): void {
  try {
    window.localStorage.setItem(key, JSON.stringify({ savedAt: new Date().toISOString(), data }));
  } catch {
    // Storage can be full or blocked. The screens still work online.
  }
}

function read<T>(key: string): Saved<T> | null {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as Saved<T>) : null;
  } catch {
    return null;
  }
}

export const saveOfflinePlan = (plan: SafetyPlan) => write(OFFLINE_KEYS.plan, plan);

/** Removes the private copy. Helplines and exercises are public and are kept. */
export function clearOfflineCopies(): void {
  try {
    window.localStorage.removeItem(OFFLINE_KEYS.plan);
  } catch {
    // Nothing to clear.
  }
}

/** Try the network; keep a copy on success; fall back to the copy on failure. */
async function networkThenCopy<T>(key: string, load: () => Promise<T>): Promise<OfflineResult<T>> {
  try {
    const data = await load();
    write(key, data);
    return { data, savedAt: null };
  } catch (error) {
    const saved = read<T>(key);
    if (saved) return saved;
    throw error;
  }
}

export function useOfflinePlan(enabled = true) {
  return useQuery({
    queryKey: ["offline", "plan"],
    queryFn: () =>
      networkThenCopy<SafetyPlan>(OFFLINE_KEYS.plan, () =>
        api("/safety-plan", { schema: safetyPlanSchema }),
      ),
    enabled,
    retry: false,
    staleTime: 0,
  });
}

export function useOfflineResources() {
  return useQuery({
    queryKey: ["offline", "resources"],
    queryFn: () =>
      networkThenCopy<Resource[]>(
        OFFLINE_KEYS.resources,
        async () => (await api("/resources?page_size=100", { schema: page(resourceSchema) })).results,
      ),
    retry: false,
  });
}

export function useOfflineExercises() {
  return useQuery({
    queryKey: ["offline", "exercises"],
    queryFn: () =>
      networkThenCopy<Exercise[]>(
        OFFLINE_KEYS.exercises,
        async () =>
          (await api("/exercises?page_size=100&include_hidden=true", { schema: page(exerciseSchema) }))
            .results,
      ),
    retry: false,
  });
}
