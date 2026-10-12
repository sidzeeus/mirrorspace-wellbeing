/**
 * Same-origin proxy to the Django API.
 *
 * The browser only ever talks to this site, so the session and CSRF cookies are
 * first-party, there is no cross-origin request to configure, and the API's address
 * is a runtime setting (API_INTERNAL_URL) rather than something baked into the bundle.
 * Nothing is cached, logged or inspected here: requests and responses pass through.
 */
import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const API = (process.env.API_INTERNAL_URL ?? "http://localhost:8000").replace(/\/$/, "");
const FORWARDED_REQUEST_HEADERS = [
  "accept",
  "accept-language",
  "content-type",
  "cookie",
  "origin",
  "referer",
  "user-agent",
  "x-csrftoken",
];
const FORWARDED_RESPONSE_HEADERS = [
  "content-type",
  "content-disposition",
  "cache-control",
  "retry-after",
  "www-authenticate",
];

async function proxy(request: NextRequest, path: string[]): Promise<Response> {
  const headers = new Headers();
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  // Lets the API rate-limit by the real client address (see NUM_PROXIES).
  const forwardedFor = request.headers.get("x-forwarded-for");
  if (forwardedFor) headers.set("x-forwarded-for", forwardedFor);
  // Pass on the scheme the visitor actually used. Behind a TLS-terminating proxy this
  // server sees plain HTTP, so the proxy's own header is the truth when present.
  headers.set(
    "x-forwarded-proto",
    request.headers.get("x-forwarded-proto") ?? request.nextUrl.protocol.replace(":", ""),
  );

  const hasBody = !["GET", "HEAD"].includes(request.method);
  let upstream: Response;
  try {
    upstream = await fetch(`${API}/api/v1/${path.join("/")}${request.nextUrl.search}`, {
      method: request.method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      redirect: "manual",
      cache: "no-store",
    });
  } catch {
    return Response.json(
      { detail: "The service cannot be reached right now. Try again in a moment.", code: "unreachable" },
      { status: 503 },
    );
  }

  const responseHeaders = new Headers();
  for (const name of FORWARDED_RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }
  for (const cookie of upstream.headers.getSetCookie()) {
    responseHeaders.append("set-cookie", cookie);
  }
  if (!responseHeaders.has("cache-control")) responseHeaders.set("cache-control", "no-store");
  const empty = upstream.status === 204 || upstream.status === 304;
  return new Response(empty ? null : upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

type Context = { params: Promise<{ path: string[] }> };
const handler = async (request: NextRequest, context: Context) =>
  proxy(request, (await context.params).path);

export { handler as DELETE, handler as GET, handler as PATCH, handler as POST, handler as PUT };
