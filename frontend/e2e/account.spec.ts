import { devices, expect, test } from "@playwright/test";

import {
  PASSWORD,
  cleanUp,
  createUser,
  expectAccessible,
  resetThrottles,
  setPrefs,
  signIn,
  uniqueEmail,
  verificationToken,
  watchConsole,
} from "./helpers";

test.beforeEach(() => resetThrottles());
test.afterAll(() => cleanUp());

test("sign up, verify, onboarding, dashboard", async ({ page }) => {
  const problems = watchConsole(page);
  const email = uniqueEmail("signup");

  // Register: the age confirmation cannot be skipped.
  await page.goto("/register");
  await expectAccessible(page);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByLabel("What should we call you?").fill("Asha");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("Confirm that you are 18 or older to continue.")).toBeVisible();
  await page.getByLabel("I am 18 or older").check();
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible();

  // Signing in before confirming is refused, with a way forward.
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Confirm your email before signing in.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Send the link again" })).toBeVisible();

  // The emailed link carries its token in the fragment.
  await page.goto(`/verify-email#token=${verificationToken(email)}`);
  await expect(page.getByText("Your email is confirmed.")).toBeVisible();
  await page.getByRole("link", { name: "Go to sign in" }).click();

  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();

  // Onboarding: the notice and age confirmation are required.
  await expect(page).toHaveURL(/\/onboarding$/);
  await expect(page.getByRole("heading", { name: "Before you start" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Support" }).first()).toBeVisible();
  await expectAccessible(page);
  await page.goto("/home");
  await expect(page).toHaveURL(/\/onboarding$/);
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByText("Tick both boxes to continue.")).toBeVisible();
  await page.getByLabel("I am 18 or older").check();
  await page.getByLabel("I have read this notice").check();
  await page.getByRole("button", { name: "Continue" }).click();

  // Preferences are optional and take effect at once.
  await expect(page.getByRole("heading", { name: "Make it comfortable" })).toBeVisible();
  await expectAccessible(page);
  await page.getByRole("switch", { name: "Larger text" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-text", "large");
  await page.getByRole("button", { name: "Skip this step" }).click();

  // Dashboard: a greeting, an invitation, no streaks.
  await expect(page).toHaveURL(/\/home$/);
  await expect(page.getByRole("heading", { name: "Hello, Asha" })).toBeVisible();
  await expect(page.getByText("Check in if you like.")).toBeVisible();
  await expect(page.getByText("No check-ins in the last seven days.")).toBeVisible();
  await expect(page.getByRole("img", { name: /Seven paw prints.*None are filled in/ })).toBeVisible();
  const text = (await page.locator("main").innerText()).toLowerCase();
  for (const word of ["streak", "missed", "keep it up", "great job", "don't break"]) {
    expect(text).not.toContain(word);
  }
  await expectAccessible(page);
  expect(problems).toEqual([]);
});

test("signed-out visitors are sent to sign in", async ({ page }) => {
  await page.goto("/home");
  await expect(page).toHaveURL(/\/login$/);
});

test("wrong password explains itself without saying which part was wrong", async ({ page }) => {
  const email = createUser();
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("not-the-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Email or password is incorrect.")).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);
});

test.describe("dashboard", () => {
  for (const theme of ["night", "daybreak"] as const) {
    test(`is accessible in ${theme} on phone and desktop`, async ({ page }) => {
      await setPrefs(page, { theme, motion: "reduced" });
      await signIn(page, createUser());
      await expect(page.getByRole("heading", { name: "Hello, Asha Rao" })).toBeVisible();
      await expectAccessible(page);
      await page.setViewportSize({ width: 1440, height: 900 });
      await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
      await expectAccessible(page);
    });
  }

  test("Support is one tap away on every screen, on phone and desktop", async ({ page }) => {
    await signIn(page, createUser());
    for (const path of ["/home", "/settings"]) {
      await page.goto(path);
      const support = page.locator("[data-support-link]:visible");
      await expect(support).toHaveCount(1);
      await expect(support).toHaveAttribute("href", "/support");
      const box = await support.boundingBox();
      expect(box?.height).toBeGreaterThanOrEqual(44);
    }
    await page.setViewportSize({ width: 1440, height: 900 });
    await expect(page.locator("[data-support-link]:visible")).toHaveCount(1);
  });

  test("keyboard reaches the navigation, and touch targets are large enough", async ({ page }) => {
    await signIn(page, createUser());
    await page.goto("/home");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
    // Every section is in the navigation itself; nothing is hidden behind a menu.
    const sections = ["Home", "Check in", "Patterns", "Episodes", "Exercises", "Plan"];
    for (const name of [...sections, "Sharing", "Chat", "Helplines", "Settings"]) {
      const link = page.getByRole("navigation", { name: "Main" }).getByRole("link", { name, exact: true });
      await expect(link).toBeVisible();
      const box = await link.boundingBox();
      expect(box?.height).toBeGreaterThanOrEqual(44);
    }
    await expect(
      page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Home", exact: true }),
    ).toHaveAttribute("aria-current", "page");
  });

  test("reduced motion and low-bandwidth mode show a still week", async ({ browser }) => {
    const email = createUser();
    const context = await browser.newContext({ ...devices["Pixel 7"], reducedMotion: "reduce" });
    const page = await context.newPage();
    await signIn(page, email);
    await expect(page.locator("[data-week]")).toBeVisible();
    // The pets hold still: every animation runs once, instantly.
    const body = page.locator(".pet .pet-body").first();
    expect(await body.evaluate((element) => getComputedStyle(element).animationIterationCount)).toBe("1");
    await expect(page.locator("canvas")).toHaveCount(0);

    await page.evaluate(() => localStorage.setItem("prefs", JSON.stringify({ bandwidth: "low" })));
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-bandwidth", "low");
    await expect(page.locator("canvas")).toHaveCount(0);
    await context.close();
  });

  test("signing out returns to the public page and clears the session", async ({ page }) => {
    await signIn(page, createUser());
    await page.goto("/settings");
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/$/);
    await page.goto("/home");
    await expect(page).toHaveURL(/\/login$/);
  });
});

test("from Helplines, a signed-in person gets back into the app, not to sign-up", async ({ page }) => {
  await signIn(page, createUser());
  await page.goto("/home");
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Helplines", exact: true }).first().click();
  await expect(page).toHaveURL(/\/resources$/);
  await expect(page.getByRole("link", { name: "Sign in" })).toHaveCount(0);
  await expect(page.locator("[data-back-to-app]")).toBeVisible();

  // The app's name leads home, not to the start page.
  await page.getByRole("link", { name: "Mirrorspace" }).click();
  await expect(page).toHaveURL(/\/home$/);

  // And the Back button returns to where you were.
  await page.goto("/home");
  await page.goto("/resources");
  await page.locator("[data-back]").click();
  await expect(page).toHaveURL(/\/home$/);
});
