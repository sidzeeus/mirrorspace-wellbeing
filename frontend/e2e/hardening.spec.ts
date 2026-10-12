/**
 * Localization, layout at large text, installability and the bundle budget
 * (README Prompt 6).
 */
import { type Page, expect, test } from "@playwright/test";

import { cleanUp, createUser, expectAccessible, resetThrottles, setPrefs, signIn } from "./helpers";

test.beforeEach(() => resetThrottles());
test.afterAll(() => cleanUp());

const SMALL_PHONE = { width: 320, height: 640 };
const APP_SCREENS = [
  "/home",
  "/check-in",
  "/patterns",
  "/episodes",
  "/exercises",
  "/plan",
  "/sharing",
  "/settings",
  "/more",
  "/support",
];

async function useHindi(page: Page): Promise<void> {
  await page.context().addCookies([{ name: "locale", value: "hi", url: "http://localhost:3000" }]);
}

async function expectNoSidewaysScroll(page: Page): Promise<void> {
  const overflow = await page.evaluate(() => {
    const root = document.scrollingElement!;
    return root.scrollWidth - root.clientWidth;
  });
  expect(overflow, `${page.url()} scrolls sideways by ${overflow}px`).toBeLessThanOrEqual(1);
}

test.describe("localization", () => {
  test("Hindi switches the language, the script font and the line height", async ({ page }) => {
    await useHindi(page);
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("lang", "hi");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("अपने पैटर्न पहचानें");
    await expect(page.getByRole("link", { name: "खाता बनाएँ" }).first()).toBeVisible();
    // Strings without a translation fall back to English instead of showing a key.
    await expect(page.getByRole("heading", { name: "What this is not" })).toBeVisible();
    expect(await page.locator("main").innerText()).not.toMatch(/landing\.[a-z]+\./);

    const style = await page.evaluate(() => {
      const computed = getComputedStyle(document.body);
      return { family: computed.fontFamily, ratio: parseFloat(computed.lineHeight) / parseFloat(computed.fontSize) };
    });
    expect(style.family).toMatch(/Noto.Sans.Devanagari/i);
    expect(style.ratio).toBeGreaterThanOrEqual(1.75);
    await expectAccessible(page);
  });

  test("the language selector changes the interface and is remembered", async ({ page }) => {
    await signIn(page, createUser());
    await page.goto("/settings");
    await page.getByLabel("Language").selectOption("hi");
    await expect(page.locator("html")).toHaveAttribute("lang", "hi");
    await expect(page.getByRole("navigation", { name: "मुख्य" }).getByRole("link", { name: "होम" })).toBeVisible();

    await page.goto("/home");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("नमस्ते");
    const saved = await page.evaluate(async () => (await (await fetch("/api/v1/auth/me")).json()).preferred_language);
    expect(saved).toBe("hi");

    await page.goto("/settings");
    await page.getByLabel("Language").selectOption("en");
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
  });

  for (const locale of ["en", "hi"] as const) {
    test(`no screen scrolls sideways at 320px with larger text (${locale})`, async ({ page }) => {
      test.setTimeout(240_000);
      if (locale === "hi") await useHindi(page);
      await setPrefs(page, { text: "large", motion: "reduced" });
      await page.setViewportSize(SMALL_PHONE);

      for (const path of ["/", "/login", "/register", "/resources"]) {
        await page.goto(path);
        await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
        await expectNoSidewaysScroll(page);
      }
      await signIn(page, createUser({ displayName: "Anantapadmanabhan Subramaniam" }));
      for (const path of APP_SCREENS) {
        await page.goto(path);
        await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
        await expect(page.getByText("Loading", { exact: true })).toHaveCount(0);
        await expectNoSidewaysScroll(page);
      }
    });
  }

  test("Support in Hindi keeps the safety sentences and stays accessible", async ({ page }) => {
    await useHindi(page);
    await setPrefs(page, { motion: "reduced" });
    await page.goto("/support");
    await expect(page.getByRole("heading", { name: "सहायता", level: 1 })).toBeVisible();
    await expect(page.getByText("इस ऐप की निगरानी कोई नहीं करता।")).toBeVisible();
    await expect(page.getByText("आपातकालीन नंबर पर कॉल करें")).toBeVisible();
    await expectAccessible(page);
  });
});

test.describe("installable app", () => {
  test("has a manifest, icons, a service worker and an offline page", async ({ page, request }) => {
    await page.goto("/");
    const href = await page.locator("link[rel='manifest']").getAttribute("href");
    const manifest = await (await request.get(href!)).json();
    expect(manifest.display).toBe("standalone");
    expect(manifest.start_url).toBe("/home");
    expect(manifest.icons.map((icon: { sizes: string }) => icon.sizes)).toEqual(
      expect.arrayContaining(["192x192", "512x512"]),
    );
    for (const icon of manifest.icons) {
      const response = await request.get(icon.src);
      expect(response.status()).toBe(200);
      expect(response.headers()["content-type"]).toContain("image/png");
    }
    const worker = await request.get("/sw.js");
    expect(worker.status()).toBe(200);
    expect(worker.headers()["cache-control"]).toContain("no-cache");
    expect(await worker.text()).toContain('url.pathname.startsWith("/api/")');

    await page.goto("/offline");
    await expect(page.getByRole("heading", { name: "You are offline" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Open support" })).toBeVisible();
    await expectAccessible(page);
  });

  test("security headers are set on pages", async ({ request }) => {
    const headers = (await request.get("/")).headers();
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["x-frame-options"]).toBe("DENY");
    expect(headers["referrer-policy"]).toBe("same-origin");
    expect(headers["x-powered-by"]).toBeUndefined();
    expect(headers["content-security-policy"]).toContain("frame-ancestors 'none'");
    expect(headers["content-security-policy"]).toContain("object-src 'none'");
  });
});

/**
 * Bundle budget: compressed JavaScript and total font bytes per screen. The numbers
 * are ceilings with some headroom over today's sizes. If a change pushes a screen over,
 * either remove weight or raise the number here deliberately, in the same commit.
 */
const BUDGET_KB = { "/": 260, "/support": 290, "/login": 280 } as const;

async function measure(page: Page, path: string) {
  let script = 0;
  let fonts = 0;
  const pending: Promise<void>[] = [];
  page.on("response", (response) => {
    const url = response.url();
    const type = response.request().resourceType();
    if (type !== "script" && type !== "font") return;
    pending.push(
      response
        .finished()
        .then(async () => {
          const sizes = await response.request().sizes();
          if (type === "script" && url.includes("/_next/")) script += sizes.responseBodySize;
          if (type === "font") fonts += sizes.responseBodySize;
        })
        .catch(() => undefined),
    );
  });
  await page.goto(path);
  await page.waitForLoadState("networkidle");
  await Promise.all(pending);
  return { scriptKb: Math.round(script / 1024), fontKb: Math.round(fonts / 1024) };
}

test.describe("performance budget", () => {
  for (const [path, limit] of Object.entries(BUDGET_KB)) {
    test(`${path} ships at most ${limit} KB of compressed JavaScript`, async ({ page }) => {
      await setPrefs(page, { motion: "reduced" });
      const { scriptKb } = await measure(page, path);
      console.log(`bundle ${path}: ${scriptKb} KB of JavaScript (budget ${limit} KB)`);
      expect(scriptKb).toBeGreaterThan(0);
      expect(scriptKb).toBeLessThanOrEqual(limit);
    });
  }

  test("low-bandwidth mode downloads no web font and starts no canvas", async ({ page }) => {
    await setPrefs(page, { bandwidth: "low" });
    const { fontKb } = await measure(page, "/");
    expect(fontKb).toBe(0);
    await expect(page.locator("canvas")).toHaveCount(0);
    await signIn(page, createUser());
    for (const path of ["/home", "/check-in", "/exercises"]) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect(page.locator("canvas")).toHaveCount(0);
    }
  });
});
