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

async function getCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken;
  const response = await fetch("/api/v1/auth/csrf", { credentials: "same-origin" });
  const body = (await response.json()) as { csrf_token: string };
  csrfToken = body.csrf_token;
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

export async function api<S extends z.ZodTypeAny | undefined = undefined>(
  path: string,
  { method = "GET", body, schema }: Options<S> = {},
  retried = false,
): Promise<S extends z.ZodTypeAny ? z.infer<S> : unknown> {
  const headers: Record<string, string> = { Accept: "application/json" };
  let response: Response;
  try {
    if (method !== "GET") headers["X-CSRFToken"] = await getCsrfToken();
    if (body !== undefined) headers["Content-Type"] = "application/json";
    response = await fetch(`/api/v1${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "same-origin",
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "offline", "");
  }

  if (response.status === 204) return undefined as never;
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    const error = toError(response.status, payload);
    if (error.code === "csrf_failed" && !retried) {
      forgetCsrfToken();
      return api(path, { method, body, schema }, true);
    }
    throw error;
  }
  return (schema ? schema.parse(payload) : payload) as never;
}
