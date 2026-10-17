import path from "node:path";

import { devices, expect, test } from "@playwright/test";

import { expectAccessible, setPrefs, watchConsole } from "./helpers";

const SHOTS = path.resolve(__dirname, "..", "..", "docs", "screenshots");
const DESKTOP = { width: 1440, height: 900 };

test.describe("landing page", () => {
  test("says what the app is and is not, and shows helplines before sign-up", async ({ page }) => {
    const problems = watchConsole(page);
    await page.goto("/");

    await expect(page.getByRole("heading", { level: 1 })).toContainText("Notice your patterns.");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Reach real help");
    await expect(page.getByText("Not therapy, and not an emergency service.")).toBeVisible();
    await expect(page.getByRole("heading", { name: "What this is not" })).toBeVisible();
    await expect(page.getByText("Nobody reads what you enter")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Helplines you can call now" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Create an account" }).first()).toBeVisible();
    expect(problems).toEqual([]);
  });

  for (const theme of ["night", "daybreak"] as const) {
    test(`has no accessibility violations in ${theme}`, async ({ page }) => {
      await setPrefs(page, { theme, motion: "reduced" });
      await page.goto("/");
      await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
      await expectAccessible(page);
      await page.setViewportSize(DESKTOP);
      await expectAccessible(page);
    });
  }

  test("can be used with the keyboard alone", async ({ page, browserName }) => {
    test.skip(browserName !== "chromium");
    await page.setViewportSize(DESKTOP);
    await page.goto("/");

    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: "Skip to main content" });
    await expect(skip).toBeFocused();
    await expect(skip).toBeVisible();

    const reached: string[] = [];
    for (let i = 0; i < 8; i += 1) {
      await page.keyboard.press("Tab");
      reached.push(
        await page.evaluate(() => {
          const element = document.activeElement as HTMLElement | null;
          return element?.getAttribute("aria-label") ?? element?.textContent?.trim() ?? "";
        }),
      );
    }
    expect(reached).toEqual(
      expect.arrayContaining(["Helplines", "Sign in", "Create an account", "See helplines"]),
    );
    // Every focused control shows a visible focus ring.
    const outline = await page.evaluate(
      () => getComputedStyle(document.activeElement as Element).outlineStyle,
    );
    expect(outline).not.toBe("none");

    await page.keyboard.press("Home");
    await skip.focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/#main$/);
  });

  test("theme follows the system at first, then remembers the choice", async ({ browser }) => {
    const context = await browser.newContext({ ...devices["Pixel 7"], colorScheme: "light" });
    const page = await context.newPage();
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "daybreak");

    await page.getByRole("button", { name: "Switch to the dark theme" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "night");
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "night");
    await expect(page.getByRole("button", { name: "Switch to the light theme" })).toBeVisible();
    await context.close();
  });

  test("reduced motion gives still images and no canvas", async ({ browser }) => {
    const context = await browser.newContext({ ...devices["Pixel 7"], reducedMotion: "reduce" });
    const page = await context.newPage();
    await page.goto("/");

    await expect(page.locator("canvas")).toHaveCount(0);
    for (const body of await page.locator(".pet .pet-body").all()) {
      expect(await body.evaluate((element) => getComputedStyle(element).animationIterationCount)).toBe("1");
    }
    // Each step of the story still has its own image and description.
    await expect(page.getByRole("img", { name: "A fox joined by a small bunny" })).toBeVisible();
    await context.close();
  });

  test("the in-app reduced-motion setting stops the canvas", async ({ page }) => {
    await setPrefs(page, { motion: "reduced" });
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("data-motion", "reduced");
    await expect(page.locator("canvas")).toHaveCount(0);
  });

  test("low-bandwidth mode starts no canvas and drops the web fonts", async ({ page }) => {
    await setPrefs(page, { bandwidth: "low" });
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("data-bandwidth", "low");
    await expect(page.locator("canvas")).toHaveCount(0);
    const family = await page.evaluate(() => getComputedStyle(document.body).fontFamily);
    expect(family).not.toContain("Hanken");
  });

  test("with motion allowed the pets breathe and sway", async ({ page }) => {
    await page.goto("/");
    const hero = page.locator("[data-pet]").first();
    await expect(hero).toHaveAttribute("aria-label", /pink cat/);
    const body = hero.locator(".pet-body").first();
    expect(await body.evaluate((element) => getComputedStyle(element).animationIterationCount)).toBe("infinite");
  });

  test("the aurora breathes behind public pages but stays still on Support", async ({ page }) => {
    const breathing = async () => {
      const layer = page.locator(".fixed.-z-10 .absolute.inset-0 > div").first();
      await layer.waitFor({ state: "attached" });
      const first = await layer.evaluate((element) => (element as HTMLElement).style.background);
      await page.waitForTimeout(1500);
      const second = await layer.evaluate((element) => (element as HTMLElement).style.background);
      return first !== second;
    };
    await page.goto("/");
    expect(await breathing()).toBe(true);
    await page.goto("/support");
    expect(await breathing()).toBe(false);
  });

  test("works with JavaScript turned off", async ({ browser }) => {
    const context = await browser.newContext({ ...devices["Pixel 7"], javaScriptEnabled: false });
    const page = await context.newPage();
    await page.goto("/");

    await expect(page.getByRole("heading", { level: 1 })).toContainText("Notice your patterns.");
    // The pets are plain SVG drawn on the server, so they are there without JavaScript.
    expect(await page.locator("[data-pet] svg").count()).toBeGreaterThanOrEqual(4);
    // The still aurora is plain CSS, so it is there without JavaScript too.
    expect(await page.evaluate(() => getComputedStyle(document.documentElement).backgroundImage)).toContain(
      "radial-gradient",
    );
    await expect(page.getByRole("heading", { name: "Real help", exact: true })).toBeVisible();
    await page.getByRole("link", { name: "See helplines" }).click();
    await expect(page).toHaveURL(/\/resources$/);
    await context.close();
  });

  for (const theme of ["night", "daybreak"] as const) {
    test(`screenshots in ${theme}`, async ({ page }) => {
      await setPrefs(page, { theme, motion: "reduced" });
      await page.goto("/");
      await page.screenshot({ path: path.join(SHOTS, `landing-${theme}-mobile.png`), fullPage: true });
      await page.setViewportSize(DESKTOP);
      await page.screenshot({ path: path.join(SHOTS, `landing-${theme}-desktop.png`), fullPage: true });
    });
  }
});

test("background music can be turned off, and the choice is remembered", async ({ page }) => {
  await page.goto("/");
  const toggle = page.locator("[data-music-toggle]");
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
  await expect(toggle).toHaveAccessibleName("Turn background music off");
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-pressed", "false");
  await page.reload();
  await expect(page.locator("[data-music-toggle]")).toHaveAttribute("aria-pressed", "false");
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem("prefs") ?? "{}").music)).toBe("off");
});
