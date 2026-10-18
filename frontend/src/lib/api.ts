/**
 * The one way the browser talks to the API.
 *
 * Requests go to this site's own /api/v1 proxy, so the session cookie is first-party.
 * Every write carries the CSRF token. Nothing here stores, logs or caches a response.
 */
import type { z } from "zod";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly detail: string,
    /** Field name to the messages the API gave for it. */
    readonly fields: Record<string, string[]> = {},
  ) {
    super(detail || code);
  }

  /** The first message for one field, for showing next to its input. */
  field(name: string): string | undefined {
    return this.fields[name]?.[0];
  }
}

let csrfToken: string | null = null;

/** Django issues a new token when the session changes (sign-in, sign-out). */
export function forgetCsrfToken(): void {
  csrfToken = null;
}

/** Fired with `true` while the API is waking up, and `false` once it answers. */
export const WAKING_EVENT = "mirrorspace:waking";
const WAKE_RETRY_MS = 5_000;
const WAKE_GIVE_UP_MS = 150_000;

function signalWaking(waking: boolean): void {
  window.dispatchEvent(new CustomEvent(WAKING_EVENT, { detail: waking }));
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

async function getCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken;
  const response = await fetch("/api/v1/auth/csrf", { credentials: "same-origin" });
  const payload = await readJson(response);
  if (!response.ok) throw toError(response.status, payload);
  csrfToken = (payload as { csrf_token: string }).csrf_token;
  return csrfToken;
}

type Options<S extends z.ZodTypeAny | undefined> = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  /** Validates the response and gives the result its type. */
  schema?: S;
};

function toError(status: number, payload: unknown): ApiError {
  const data = (payload && typeof payload === "object" ? payload : {}) as Record<string, unknown>;
  const fields: Record<string, string[]> = {};
  for (const [key, value] of Object.entries(data)) {
    if (Array.isArray(value)) fields[key] = value.map(String);
  }
  const detail =
    typeof data.detail === "string" ? data.detail : (fields.non_field_errors?.[0] ?? "");
  const code = typeof data.code === "string" ? data.code : `http_${status}`;
  return new ApiError(status, code, detail, fields);
}

/**
 * One API call. While the API is waking up (free hosting sleeps when idle), it waits
 * and tries again for up to two and a half minutes instead of failing at once.
 */
export async function api<S extends z.ZodTypeAny | undefined = undefined>(
  path: string,
  options: Options<S> = {},
): Promise<S extends z.ZodTypeAny ? z.infer<S> : unknown> {
  const started = Date.now();
  let waking = false;
  for (;;) {
    try {
      const result = await request(path, options);
      if (waking) signalWaking(false);
      return result;
    } catch (error) {
      const retry =
        error instanceof ApiError &&
        error.code === "waking" &&
        Date.now() - started < WAKE_GIVE_UP_MS;
      if (!retry) {
        if (waking) signalWaking(false);
        throw error;
      }
      waking = true;
      signalWaking(true);
      await new Promise((resolve) => setTimeout(resolve, WAKE_RETRY_MS));
    }
  }
}

async function request<S extends z.ZodTypeAny | undefined>(
  path: string,
  { method = "GET", body, schema }: Options<S>,
  retried = false,
): Promise<S extends z.ZodTypeAny ? z.infer<S> : unknown> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") headers["X-CSRFToken"] = await withNetwork(getCsrfToken());
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const response = await withNetwork(
    fetch(`/api/v1${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "same-origin",
      cache: "no-store",
    }),
  );

  if (response.status === 204) return undefined as never;
  const payload = await readJson(response);
  if (!response.ok) {
    const error = toError(response.status, payload);
    if (error.code === "csrf_failed" && !retried) {
      forgetCsrfToken();
      return request(path, { method, body, schema }, true);
    }
    throw error;
  }
  return (schema ? schema.parse(payload) : payload) as never;
}

/** A request that never reached the server means no connection: say "offline". */
async function withNetwork<T>(pending: Promise<T>): Promise<T> {
  try {
    return await pending;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(0, "offline", "");
  }
}
