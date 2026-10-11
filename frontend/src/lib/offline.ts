"use client";

/**
 * Offline copies for the Support screen (decision D7).
 *
 * Exactly two things are kept on the device so Support works with no connection: the
 * person's own safety plan and the helpline list. Nothing else is ever stored here:
 * no check-ins, no episodes, no contacts, no chat. A browser test enforces that.
 * The copies are removed on sign-out and when the account is deleted.
 */
import type { Resource, SafetyPlan } from "./schemas";

export const OFFLINE_KEYS = {
  plan: "offline.safetyPlan",
  resources: "offline.resources",
} as const;

type Saved<T> = { savedAt: string; data: T };

function write<T>(key: string, data: T): void {
  try {
    window.localStorage.setItem(key, JSON.stringify({ savedAt: new Date().toISOString(), data }));
  } catch {
    // Storage can be full or blocked. Support still works online.
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
export const readOfflinePlan = () => read<SafetyPlan>(OFFLINE_KEYS.plan);
export const saveOfflineResources = (resources: Resource[]) =>
  write(OFFLINE_KEYS.resources, resources);
export const readOfflineResources = () => read<Resource[]>(OFFLINE_KEYS.resources);

/** Removes the private copy. The helpline list is public and is kept. */
export function clearOfflineCopies(): void {
  try {
    window.localStorage.removeItem(OFFLINE_KEYS.plan);
  } catch {
    // Nothing to clear.
  }
}
