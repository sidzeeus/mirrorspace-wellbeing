import { devices, expect, test } from "@playwright/test";

import {
  cleanUp,
  createUser,
  expectAccessible,
  lastLine,
  manage,
  resetThrottles,
  setPrefs,
  signIn,
} from "./helpers";

test.beforeAll(() => {
  manage("from django.core.management import call_command; call_command('seed_exercises')");
});
test.beforeEach(() => resetThrottles());
test.afterAll(() => cleanUp());

function eventKinds(email: string): string {
  return lastLine(
    manage(`
from apps.wellbeing.models import ExerciseEvent
print(",".join(ExerciseEvent.objects.filter(user__email=${JSON.stringify(email)}).order_by("created_at").values_list("kind", flat=True)))
`),
  );
}

test("complete an exercise and mark it not helpful", async ({ page }) => {
  const email = createUser();
  await signIn(page, email);
  await page.goto("/exercises");
  await expect(page.getByRole("heading", { name: "Exercises", level: 1 })).toBeVisible();

  // In development, unreviewed placeholders are shown without a label (decision B80);
  // in production they are not shown at all.
  await expect(page.getByText("Unreviewed placeholder")).toHaveCount(0);

  await page.getByRole("link", { name: "Start Five senses" }).click();
  const player = page.locator("[data-player]");
  await expect(player.getByRole("heading", { name: "Five senses" })).toBeVisible();
  // Distraction-free, but Support and End never go away.
  await expect(player.getByRole("link", { name: "Support" })).toBeVisible();
  await expect(player.getByRole("link", { name: "End this exercise" })).toBeVisible();
  // The player covers the whole screen, including the navigation bar.
  const covered = await page.evaluate(() => {
    const nav = document.querySelector("nav[aria-label='Main']:not([hidden])");
    const box = [...document.querySelectorAll("nav[aria-label='Main']")]
      .map((element) => element.getBoundingClientRect())
      .find((rect) => rect.width > 0);
    if (!nav || !box) return false;
    const top = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
    return Boolean(top?.closest("[data-player]"));
  });
  expect(covered).toBe(true);

  await expect(player.getByText("Step 1 of 5")).toBeVisible();
  await expect(player.getByRole("button", { name: "Back" })).toBeDisabled();
  for (let step = 2; step <= 5; step += 1) {
    await player.getByRole("button", { name: "Next" }).click();
    await expect(player.getByText(`Step ${step} of 5`)).toBeVisible();
  }
  await expectAccessible(page);
  await player.getByRole("button", { name: "Finish" }).click();

  await expect(player.getByRole("heading", { name: "That is the end" })).toBeVisible();
  await player.getByRole("button", { name: "Not helpful" }).click();
  await expect(player.getByText("Thank you.")).toBeVisible();
  await expect.poll(() => eventKinds(email)).toBe("completed,not_helpful");
});

test("every exercise offers Not helpful and Hide this, and hiding can be undone", async ({ page }) => {
  const email = createUser();
  await signIn(page, email);
  await page.goto("/exercises");

  const items = page.locator("[data-exercise]");
  await expect(items.first()).toBeVisible();
  const total = await items.count();
  expect(total).toBeGreaterThanOrEqual(6);
  for (let index = 0; index < total; index += 1) {
    await expect(items.nth(index).getByRole("button", { name: /as not helpful$/ })).toBeVisible();
    await expect(items.nth(index).getByRole("button", { name: /^Hide / })).toBeVisible();
  }

  await page.getByRole("button", { name: "Hide Three lines" }).click();
  await expect(page.locator("[data-exercise='three-lines']")).toHaveCount(0);
  await expect(page.getByText("Hidden. You will not be offered this one.", { exact: true })).toBeVisible();

  await page.getByRole("switch", { name: "Show exercises I have hidden" }).click();
  await expect(page.locator("[data-exercise='three-lines']")).toContainText("Hidden");
  await page.getByRole("button", { name: "Show Three lines again" }).click();
  await page.getByRole("switch", { name: "Show exercises I have hidden" }).click();
  await expect(page.locator("[data-exercise='three-lines']")).toBeVisible();

  await page.getByRole("button", { name: "Mark Screens down as not helpful" }).click();
  await expect(page.getByText("Noted. Thank you.", { exact: true })).toBeVisible();
  await expect.poll(() => eventKinds(email)).toBe("hidden,unhidden,not_helpful");

  // Filters only offer groups that have something in them.
  await page.getByRole("button", { name: "Breathing", exact: true }).click();
  await expect(items).toHaveCount(1);
  await expectAccessible(page);
});

test("breathing: reduced motion uses a progress ring and words", async ({ browser }) => {
  const email = createUser();
  const context = await browser.newContext({ ...devices["Pixel 7"], reducedMotion: "reduce" });
  const page = await context.newPage();
  await signIn(page, email);
  await page.goto("/exercises");
  await page.getByRole("link", { name: "Start Slow breathing" }).click();

  const player = page.locator("[data-player]");
  await expect(player.getByRole("progressbar")).toBeVisible();
  await expect(player.locator("canvas")).toHaveCount(0);
  await expect(player.getByText("Start when you are ready").first()).toBeVisible();

  // Adjustable pace, default four in and six out.
  await expect(player.getByText("Breathe in for 4 seconds")).toBeVisible();
  await expect(player.getByText("Breathe out for 6 seconds")).toBeVisible();
  await player.getByRole("button", { name: "Longer in-breath" }).click();
  await expect(player.getByText("Breathe in for 5 seconds")).toBeVisible();

  await player.getByRole("button", { name: "Start" }).click();
  await expect(player.getByRole("progressbar")).toHaveAttribute("aria-label", /Breathe in, \d seconds left/);
  await expect(player.getByRole("button", { name: "Pause" })).toBeVisible();
  // Sound and vibration are optional and off until chosen.
  await expect(player.getByRole("switch", { name: "Sound cue" })).not.toBeChecked();
  await expect(player.getByRole("switch", { name: "Vibration cue" })).not.toBeChecked();
  await expectAccessible(page);

  // Ending early is always possible.
  await player.getByRole("button", { name: "Finish" }).click();
  await expect(player.getByRole("heading", { name: "That is the end" })).toBeVisible();
  await player.getByRole("link", { name: "Skip" }).click();
  await expect(page).toHaveURL(/\/exercises$/);
  await context.close();
});

test("breathing: with motion allowed the pet carries the breath", async ({ page }) => {
  await signIn(page, createUser());
  await page.goto("/exercises");
  await page.getByRole("link", { name: "Start Slow breathing" }).click();
  const figure = page.locator("[data-player] [data-pet]");
  await expect(figure).toHaveAttribute("aria-label", /grows as you breathe in/);
  await page.locator("[data-player]").getByRole("button", { name: "Start" }).click();
  await expect(figure).toHaveAttribute("aria-label", /Breathe (in|out)/);
});

test("an exercise opened once still opens offline", async ({ page, context }) => {
  await setPrefs(page, { motion: "reduced" });
  await signIn(page, createUser());
  await page.goto("/exercises");
  await page.getByRole("link", { name: "Start Five senses" }).click();
  await expect(page.locator("[data-player]").getByText("Step 1 of 5")).toBeVisible();
  const url = page.url();
  // Wait until the service worker controls the page and has the scripts it needs.
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.reload();
  await expect(page.locator("[data-player]").getByText("Step 1 of 5")).toBeVisible();
  await expect.poll(() => page.evaluate(() => Boolean(navigator.serviceWorker.controller))).toBe(true);

  await context.setOffline(true);
  await page.goto(url);
  const player = page.locator("[data-player]");
  await expect(player.getByRole("heading", { name: "Five senses" })).toBeVisible();
  await player.getByRole("button", { name: "Next" }).click();
  await expect(player.getByText("Step 2 of 5")).toBeVisible();
  await context.setOffline(false);
});
