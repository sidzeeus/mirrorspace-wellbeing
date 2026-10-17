import { expect, test } from "@playwright/test";

import {
  cleanUp,
  createUser,
  expectAccessible,
  lastLine,
  manage,
  resetThrottles,
  setPrefs,
  signIn,
  watchConsole,
} from "./helpers";

test.beforeEach(() => resetThrottles());
test.afterAll(() => cleanUp());

/** A week where shorter sleep goes with lower energy, to produce one observation. */
function seedWeek(email: string): void {
  manage(`
from datetime import timedelta
from apps.accounts.models import User
from apps.checkins.models import CheckIn
from apps.checkins.dates import local_today
u = User.objects.get(email=${JSON.stringify(email)})
today = local_today(u)
for days_ago, sleep, energy in [(1,5,2),(2,5,1),(3,5.5,2),(4,8,4),(5,8,5),(6,8.5,4),(7,8,4)]:
    CheckIn.objects.create(user=u, local_date=today - timedelta(days=days_ago), timezone="Asia/Kolkata", sleep_hours=sleep, energy=energy, mood=3, stress=3)
`);
}

test("sign in, check in, see the trend", async ({ page }) => {
  const problems = watchConsole(page);
  const email = createUser();
  seedWeek(email);
  await signIn(page, email);

  const started = Date.now();
  await page.getByRole("link", { name: "Check in", exact: true }).first().click();
  await expect(page.getByRole("heading", { name: "Check in" })).toBeVisible();
  // Skipping is always on screen.
  await expect(page.getByRole("link", { name: "Skip for now" })).toBeVisible();

  // The mood slider changes how the pet sits, with the same information in words.
  const lumen = page.locator("main [data-pet]");
  await expect(lumen).toHaveAttribute("aria-label", /sits quietly, waiting/);
  const slider = page.getByRole("slider", { name: "Mood" });
  await slider.focus();
  await page.keyboard.press("End");
  await expect(slider).toHaveAttribute("aria-valuetext", "5: Very high");
  await expect(lumen).toHaveAttribute("aria-label", /hops a little/);
  await expect(lumen).toHaveAttribute("data-mood", "lighter");
  await page.keyboard.press("Home");
  await expect(lumen).toHaveAttribute("aria-label", /lies low/);
  await expect(lumen).toHaveAttribute("data-mood", "heavy");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await expect(slider).toHaveAttribute("aria-valuetext", "4: High");

  await page.getByRole("button", { name: "Half an hour more" }).click();
  await expect(page.getByText("7 hours")).toBeVisible();
  await page.getByRole("group", { name: "Energy" }).getByRole("button", { name: /^4:/ }).click();
  await page.getByRole("button", { name: "Save check-in" }).click();
  await expect(page.getByText("Check-in saved.")).toBeVisible();
  expect(Date.now() - started, "a check-in should fit in twenty seconds").toBeLessThan(20_000);

  // Exactly one optional suggestion, and declining is as prominent as accepting.
  const open = page.getByRole("link", { name: "Open this exercise" });
  const notNow = page.getByRole("link", { name: "Not now" });
  await expect(open).toHaveCount(1);
  const [openBox, notNowBox] = [await open.boundingBox(), await notNow.boundingBox()];
  expect(Math.abs(openBox!.width - notNowBox!.width)).toBeLessThan(2);
  expect(Math.abs(openBox!.height - notNowBox!.height)).toBeLessThan(2);
  expect(await open.getAttribute("class")).toBe(await notNow.getAttribute("class"));
  await expectAccessible(page);
  await notNow.click();
  await expect(page.getByText("You checked in today.")).toBeVisible();
  await expect(page.getByText(/Check-ins? on \d+ days?/)).toBeVisible();

  // The trend: a chart with a text description, a table, and plain observations.
  await page.goto("/patterns");
  await expect(page.getByRole("img", { name: /Mood over the last 28 days\. 8 entries, from 3 to 4\./ })).toBeVisible();
  await page.getByText("Show the numbers as a table").click();
  await expect(page.getByRole("table")).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Sleep hours" })).toBeVisible();
  expect(await page.getByRole("row").count()).toBe(9);
  await expect(page.locator("[data-observation='check_in_count']")).toHaveText(
    "You checked in on 8 of the last 28 days.",
  );
  await expect(page.locator("[data-observation='sleep_energy_lower']")).toHaveText(
    "On days you logged less sleep than your usual, you rated your energy lower on average.",
  );
  await expect(page.getByText("They are not a diagnosis")).toBeVisible();

  await page.getByRole("button", { name: "Energy", exact: true }).click();
  await expect(page.getByRole("img", { name: /Energy over the last 28 days/ })).toBeVisible();
  await page.getByRole("button", { name: "7 days" }).click();
  await expect(page.getByRole("img", { name: /Energy over the last 7 days/ })).toBeVisible();
  await expectAccessible(page);
  expect(problems).toEqual([]);
});

test("an empty check-in is not saved, and skipping stores nothing", async ({ page }) => {
  const email = createUser();
  await signIn(page, email);
  await page.goto("/check-in");
  await page.getByRole("button", { name: "Save check-in" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Choose at least one answer" })).toBeVisible();
  await page.getByRole("link", { name: "Skip for now" }).click();
  await expect(page).toHaveURL(/\/home$/);
  const count = manage(`
from apps.checkins.models import CheckIn
print(CheckIn.objects.filter(user__email=${JSON.stringify(email)}).count())
`);
  expect(lastLine(count)).toBe("0");
});

test("check-in has no free-text field", async ({ page }) => {
  await signIn(page, createUser());
  await page.goto("/check-in");
  await expect(page.getByRole("heading", { name: "Check in" })).toBeVisible();
  // (The slider keeps one hidden input for form posts; only visible fields count.)
  await expect(
    page.locator("main textarea:visible, main input[type='text']:visible, main input:not([type]):visible"),
  ).toHaveCount(0);
});

for (const theme of ["night", "daybreak"] as const) {
  test(`check-in, patterns and episodes are accessible in ${theme}`, async ({ page }) => {
    await setPrefs(page, { theme, motion: "reduced" });
    const email = createUser();
    seedWeek(email);
    await signIn(page, email);
    for (const path of ["/check-in", "/patterns", "/episodes"]) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect(page.getByText("Loading")).toHaveCount(0);
      await expectAccessible(page);
    }
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/patterns");
    await expect(page.locator("[data-chart]")).toBeVisible();
    await expectAccessible(page);
  });
}

test("log an episode with a trigger, then archive the trigger", async ({ page }) => {
  await signIn(page, createUser());
  await page.goto("/episodes");

  await page.getByRole("tab", { name: "Triggers" }).click();
  await page.getByRole("button", { name: "Add trigger" }).click();
  await expect(page.getByText("Give the trigger a short name.")).toBeVisible();
  await page.getByLabel("Name").fill("Exam week");
  await page.getByRole("button", { name: "Add trigger" }).click();
  await expect(page.getByRole("listitem").filter({ hasText: "Exam week" })).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("tab", { name: "Episodes" }).click();
  await page.getByRole("button", { name: "Save episode" }).click();
  await expect(page.getByText("Choose an intensity from 1 to 5 to save.")).toBeVisible();
  await page.getByRole("group", { name: "How intense was it?" }).getByRole("button", { name: /^4:/ }).click();
  await page.getByLabel("About how long?").selectOption("15");
  await page.getByLabel("Did something come before it?").selectOption({ label: "Exam week" });
  await page.getByLabel("What helped, in your words").fill("A walk with a friend");
  await page.getByRole("button", { name: "Save episode" }).click();

  const logged = page.getByRole("listitem").filter({ hasText: "Intensity 4 of 5" });
  await expect(logged).toContainText("15 min");
  await expect(logged).toContainText("Before it: Exam week");
  await expect(logged).toContainText("Helped: A walk with a friend");

  await page.getByRole("tab", { name: "Triggers" }).click();
  await page.getByRole("button", { name: "Archive Exam week" }).click();
  await expect(page.getByRole("listitem").filter({ hasText: "Exam week" })).toHaveCount(0);
  await page.getByRole("switch", { name: "Show archived triggers" }).click();
  await expect(page.getByRole("button", { name: "Restore Exam week" })).toBeVisible();

  // Archived triggers are no longer offered when logging.
  await page.getByRole("tab", { name: "Episodes" }).click();
  await expect(page.getByLabel("Did something come before it?").getByRole("option", { name: "Exam week" })).toHaveCount(0);
});

test("the interface never applies a clinical label", async ({ page }) => {
  const email = createUser();
  seedWeek(email);
  await signIn(page, email);
  for (const path of ["/home", "/check-in", "/patterns", "/episodes"]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const text = (await page.locator("main").innerText()).toLowerCase();
    for (const word of ["anxious", "depressed", "disorder", "symptom", "you are at risk", "diagnosed"]) {
      expect(text, `${path} contains "${word}"`).not.toContain(word);
    }
  }
});
