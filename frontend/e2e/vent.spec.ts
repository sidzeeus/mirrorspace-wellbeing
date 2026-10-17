import { expect, test } from "@playwright/test";

import { createUser, expectAccessible, lastLine, manage, setPrefs, signIn } from "./helpers";

function keptEntries(email: string): string {
  return lastLine(
    manage(
      `from apps.vent.models import VentEntry; print(VentEntry.objects.filter(user__email=${JSON.stringify(email)}).count())`,
    ),
  );
}

function notifications(email: string): string {
  return lastLine(
    manage(
      `from apps.notifications.models import Notification; print(Notification.objects.filter(user__email=${JSON.stringify(email)}).count())`,
    ),
  );
}

test("venting reacts to the words, keeps nothing by default, and keeping is a choice", async ({ page }) => {
  const email = createUser();
  await signIn(page, email);
  await page.goto("/vent");
  await expect(page.getByRole("heading", { name: "Vent", level: 1 })).toBeVisible();
  await expect(page.getByText("Nobody reads this.")).toBeVisible();

  // Released: the figure reacts, the text clears, nothing is stored.
  await page.getByLabel("What is on your mind").fill("Nobody talks to me, I feel so lonely");
  await page.getByRole("button", { name: "Let it out" }).click();
  const reaction = page.locator("[data-vent-reaction]");
  await expect(reaction).toHaveAttribute("data-vent-reaction", "alone");
  await expect(reaction).toContainText("Released. Nothing was saved.");
  await expect(page.getByRole("img", { name: /little bunny comes to sit beside Sushi/ })).toBeVisible();
  await expect(page.getByLabel("What is on your mind")).toHaveValue("");
  expect(keptEntries(email)).toBe("0");

  // Kept: only when the switch is turned on.
  await page.getByLabel("What is on your mind").fill("So angry and fed up with this unfair week");
  await page.getByRole("switch", { name: /Keep this entry/ }).click();
  await page.getByRole("button", { name: "Let it out" }).click();
  await expect(reaction).toHaveAttribute("data-vent-reaction", "storm");
  await expect(reaction).toContainText("Kept. Only you can read it.");
  await expect(page.locator("[data-vent-entry]")).toHaveCount(1);
  expect(keptEntries(email)).toBe("1");

  await page.locator("[data-vent-entry] summary").click();
  await expect(page.locator("[data-vent-entry]")).toContainText("unfair week");
  await page.getByRole("button", { name: /Delete the entry from/ }).click();
  await expect(page.locator("[data-vent-entry]")).toHaveCount(0);
  expect(keptEntries(email)).toBe("0");
});

test("crisis wording gets a steady figure and routes to Support, and nobody is alerted", async ({ page }) => {
  const email = createUser();
  await signIn(page, email);
  await page.goto("/vent");
  await page.getByLabel("What is on your mind").fill("I want to kill myself");
  await page.getByRole("button", { name: "Let it out" }).click();

  const reaction = page.locator("[data-vent-reaction]");
  await expect(reaction).toHaveAttribute("data-vent-reaction", "steady");
  await expect(reaction).toContainText("Nobody has been told");
  await expect(reaction).toContainText("call your local emergency number");
  await expect(reaction.getByRole("link", { name: "Open Support" })).toHaveAttribute("href", "/support");
  await expect(reaction.getByRole("link", { name: "Call a helpline" })).toBeVisible();
  expect(notifications(email)).toBe("0");
  expect(keptEntries(email)).toBe("0");
});

test("the check-in links to Vent but stays taps only", async ({ page }) => {
  await signIn(page, createUser());
  await page.goto("/check-in");
  await page.getByRole("link", { name: "Write it out in Vent" }).click();
  await expect(page).toHaveURL(/\/check-in\?tab=vent$/);
});

for (const theme of ["night", "daybreak"] as const) {
  test(`vent is accessible in ${theme}`, async ({ page }) => {
    await setPrefs(page, { theme, motion: "reduced" });
    await signIn(page, createUser());
    await page.goto("/vent");
    await expectAccessible(page);
    await page.getByLabel("What is on your mind").fill("Feeling tired and empty today");
    await page.getByRole("button", { name: "Let it out" }).click();
    await expect(page.locator("[data-vent-reaction]")).toHaveAttribute("data-vent-reaction", "heavy");
    await expectAccessible(page);
  });
}
