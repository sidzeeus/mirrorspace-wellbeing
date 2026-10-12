import { type Page, expect, test } from "@playwright/test";

import {
  cleanUp,
  createContact,
  createUser,
  expectAccessible,
  lastLine,
  manage,
  resetThrottles,
  setPrefs,
  signIn,
} from "./helpers";

test.beforeAll(() => {
  manage("from django.core.management import call_command; call_command('seed_resources')");
});
test.beforeEach(() => resetThrottles());
test.afterAll(() => cleanUp());

function sosCount(email: string): string {
  return lastLine(
    manage(`
from apps.notifications.models import Notification
print(Notification.objects.filter(user__email=${JSON.stringify(email)}, purpose="sos").count())
`),
  );
}

async function openSupport(page: Page): Promise<void> {
  await page.locator("[data-support-link]:visible").click();
  await expect(page).toHaveURL(/\/support$/);
  await expect(page.getByRole("heading", { name: "Support", level: 1 })).toBeVisible();
}

test("Support opens in one tap and offers four clear options", async ({ page }) => {
  await signIn(page, createUser());
  await openSupport(page);

  const options = page.getByRole("navigation", { name: "Support options" }).getByRole("link");
  await expect(options).toHaveCount(4);
  for (const name of ["A calming exercise", "My safety plan", "Message a trusted person", "Call a helpline"]) {
    const option = options.filter({ hasText: name });
    await expect(option).toBeVisible();
    expect((await option.boundingBox())!.height).toBeGreaterThanOrEqual(44);
  }
  // Plain statements of the limits, on the screen itself.
  await expect(page.getByText("This app is not monitored.")).toBeVisible();
  await expect(page.getByText("cannot guarantee that anyone will respond")).toBeVisible();
  await expect(page.getByText("call your local emergency number").first()).toBeVisible();

  // Nothing moves until the person asks for the breathing aid.
  await expect(page.locator("canvas")).toHaveCount(0);
  await expect(page.locator("[data-lumen]")).toHaveCount(0);
  await page.getByRole("button", { name: "A calming exercise" }).click();
  await expect(page.getByText("Breathe in for 4 seconds")).toBeVisible();
});

test("SOS send path: exact recipient and message, explicit confirmation", async ({ page }) => {
  const email = createUser({ displayName: "Asha Rao" });
  createContact(email, { name: "Meera Iyer", contactEmail: "meera.sos@e2e.test" });
  await signIn(page, email);
  await openSupport(page);

  await page.getByRole("link", { name: /Message a trusted person/ }).click();
  await page.getByRole("button", { name: "Message Meera Iyer" }).click();

  // The review shows exactly who and exactly what, before anything is sent.
  const review = page.locator("[data-sos-review]");
  await expect(review.getByRole("heading", { name: "Review before sending" })).toBeVisible();
  await expect(review.locator("[data-sos-recipient]")).toHaveText("Meera Iyer (meera.sos@e2e.test)");
  await expect(review.getByText("Asha Rao would like to hear from you")).toBeVisible();
  const body = await review.locator("[data-sos-body]").innerText();
  expect(body).toContain("Asha Rao asked Mirrorspace to send you this message.");
  expect(body).toContain("not monitored");
  expect(body).toContain("To stop receiving these messages");
  expect(sosCount(email), "nothing is sent by previewing").toBe("0");
  await expectAccessible(page);

  await review.getByRole("button", { name: "Send this message" }).click();
  await expect(page.getByRole("heading", { name: "Queued to send" })).toBeVisible();
  const reply = (await page.locator("#message").innerText()).toLowerCase();
  expect(reply).toContain("queued to send");
  expect(reply).toContain("cannot tell you whether it has been read");
  for (const claim of ["delivered", "has been sent", "alerted", "on their way"]) {
    expect(reply).not.toContain(claim);
  }
  expect(sosCount(email)).toBe("1");

  // What was sent is what was shown.
  const sent = lastLine(
    manage(`
from apps.notifications.models import Notification
n = Notification.objects.get(user__email=${JSON.stringify(email)}, purpose="sos")
print(n.contact.email + "|" + n.status)
`),
  );
  expect(sent.split("|")[0]).toBe("meera.sos@e2e.test");
});

test("SOS cancel path: backing out sends nothing", async ({ page }) => {
  const email = createUser();
  createContact(email, { name: "Meera Iyer", contactEmail: "meera.cancel@e2e.test" });
  await signIn(page, email);
  await openSupport(page);

  await page.getByRole("button", { name: "Message Meera Iyer" }).click();
  await expect(page.locator("[data-sos-review]")).toBeVisible();
  await page.getByRole("button", { name: "Do not send" }).click();

  await expect(page.getByText("Nothing was sent.")).toBeVisible();
  await expect(page.locator("[data-sos-review]")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Message Meera Iyer" })).toBeVisible();
  expect(sosCount(email)).toBe("0");
});

test("a contact who has not accepted cannot be messaged", async ({ page }) => {
  const email = createUser();
  createContact(email, { name: "Pending Person", contactEmail: "pending@e2e.test", status: "pending" });
  await signIn(page, email);
  await openSupport(page);
  await expect(page.getByText("Nobody has agreed to receive messages from you yet.")).toBeVisible();
  await expect(page.getByRole("button", { name: /Message Pending/ })).toHaveCount(0);
});

test("safety plan: write, view, print, and see it in Support", async ({ page }) => {
  await signIn(page, createUser());
  await page.goto("/plan");
  await expect(page.getByText("Nothing written yet.")).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("button", { name: "Write my plan" }).click();
  await page.getByLabel("My warning signs").fill("Skipping meals\nNot replying to messages");
  await page.getByLabel("Things I can do").fill("Walk to the end of the road");
  await page.getByLabel("People I can reach").fill("Meera, my sister");
  await expectAccessible(page);
  await page.getByRole("button", { name: "Save plan" }).click();

  const view = page.locator("[data-plan-view]");
  await expect(view.getByText("Skipping meals")).toBeVisible();
  await expect(view.getByText("Not replying to messages")).toBeVisible();
  await expect(page.getByRole("button", { name: "Print" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Edit plan" })).toBeVisible();

  // The printable view drops navigation and buttons.
  await page.emulateMedia({ media: "print" });
  await expect(view.getByText("Walk to the end of the road")).toBeVisible();
  await expect(page.getByRole("button", { name: "Print" })).toBeHidden();
  await expect(page.locator("[data-support-link]:visible")).toHaveCount(0);
  await page.emulateMedia({ media: "screen" });

  await openSupport(page);
  await expect(page.locator("#plan").getByText("Meera, my sister")).toBeVisible();
});

test("Support works offline with the saved plan and helplines, and caches nothing private", async ({
  page,
  context,
}) => {
  await setPrefs(page, { motion: "reduced" });
  const email = createUser();
  await signIn(page, email);

  // Some private data that must never reach the offline stores.
  await page.goto("/check-in");
  await page.getByRole("group", { name: "Stress" }).getByRole("button", { name: /^5:/ }).click();
  await page.getByRole("button", { name: "Save check-in" }).click();
  await expect(page.getByText("Check-in saved.")).toBeVisible();

  await page.goto("/plan");
  await page.getByRole("button", { name: "Write my plan" }).click();
  await page.getByLabel("My warning signs").fill("OFFLINE-PLAN-LINE");
  await page.getByRole("button", { name: "Save plan" }).click();
  await expect(page.locator("[data-plan-view]")).toBeVisible();

  await page.goto("/support");
  await expect(page.locator("#call").getByText("Tele-MANAS")).toBeVisible();
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.reload();
  await expect.poll(() => page.evaluate(() => Boolean(navigator.serviceWorker.controller))).toBe(true);
  await expect(page.locator("#plan").getByText("OFFLINE-PLAN-LINE")).toBeVisible();

  await context.setOffline(true);
  await page.goto("/support");

  await expect(page.getByRole("heading", { name: "Support", level: 1 })).toBeVisible();
  await expect(page.getByText("You are offline. Your saved plan and helplines are still here.")).toBeVisible();
  await expect(page.locator("#plan").getByText("OFFLINE-PLAN-LINE")).toBeVisible();
  await expect(page.locator("#plan").getByText(/copy saved on this device/)).toBeVisible();
  const call = page.locator("#call").getByRole("link", { name: /Call Tele-MANAS on 14416/ });
  await expect(call).toHaveAttribute("href", "tel:14416");
  await expect(page.locator("#message").getByText("Sending a message needs a connection.")).toBeVisible();
  // The breathing aid needs no network either.
  await page.getByRole("button", { name: "A calming exercise" }).click();
  await expect(page.getByRole("progressbar")).toBeVisible();

  // The service worker cache holds pages and assets, and no API response at all.
  const cached = await page.evaluate(async () => {
    const urls: string[] = [];
    for (const name of await caches.keys()) {
      for (const request of await (await caches.open(name)).keys()) urls.push(new URL(request.url).pathname);
    }
    return urls;
  });
  expect(cached).toContain("/support");
  expect(cached.filter((path) => path.startsWith("/api/"))).toEqual([]);

  // Device storage holds only the allowed keys, and nothing from the check-in.
  const storage = await page.evaluate(() => ({ ...localStorage }));
  const allowed = ["prefs", "offline.safetyPlan", "offline.resources", "offline.exercises"];
  expect(Object.keys(storage).filter((key) => !allowed.includes(key))).toEqual([]);
  const dump = JSON.stringify(storage).toLowerCase();
  for (const word of ["stress", "mood", "sleep_hours", "energy", "episode", "trigger", "email"]) {
    expect(dump, `device storage mentions "${word}"`).not.toContain(word);
  }

  // A page that was never saved falls back to the offline screen, with Support on it.
  await page.goto("/patterns");
  await expect(page.getByRole("heading", { name: "You are offline" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open support" })).toBeVisible();
  await context.setOffline(false);
});

test("signing out removes the saved plan from the device", async ({ page }) => {
  await signIn(page, createUser());
  await page.goto("/plan");
  await page.getByRole("button", { name: "Write my plan" }).click();
  await page.getByLabel("My warning signs").fill("Private line");
  await page.getByRole("button", { name: "Save plan" }).click();
  await expect(page.locator("[data-plan-view]")).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("offline.safetyPlan"))).toContain("Private line");

  await page.goto("/more");
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/$/);
  expect(await page.evaluate(() => localStorage.getItem("offline.safetyPlan"))).toBeNull();
});

test("signed-out visitors still get helplines and the limits on Support", async ({ page }) => {
  await page.goto("/support");
  await expect(page.getByText("This app is not monitored.")).toBeVisible();
  await expect(page.locator("#call").getByText("Tele-MANAS")).toBeVisible();
  await expect(page.getByRole("link", { name: "Sign in to see your plan." })).toBeVisible();
  await expect(page.getByRole("link", { name: "Sign in to message a trusted person." })).toBeVisible();
});

for (const theme of ["night", "daybreak"] as const) {
  test(`Support, plan and helplines are accessible in ${theme}`, async ({ page }) => {
    await setPrefs(page, { theme, motion: "reduced" });
    const email = createUser();
    createContact(email, { name: "Meera Iyer", contactEmail: `meera.${theme}@e2e.test` });
    await signIn(page, email);
    for (const path of ["/support", "/plan", "/resources"]) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expectAccessible(page);
    }
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/support");
    await expect(page.getByRole("button", { name: "Message Meera Iyer" })).toBeVisible();
    await expectAccessible(page);
  });
}

test("stale and unverified helplines are flagged in words", async ({ page }) => {
  await page.goto("/resources");
  const entry = page.getByRole("listitem").filter({ hasText: "Tele-MANAS" });
  await expect(entry.getByText("Not verified yet")).toBeVisible();
  await expect(entry.getByText("Not checked yet")).toBeVisible();
  await expect(entry.getByText("This entry has not been checked recently.")).toBeVisible();
  await expect(entry.getByText("IN", { exact: true })).toBeVisible();
  await expect(entry.getByText("Helpline", { exact: true })).toBeVisible();
  await expect(entry.getByRole("link", { name: "Call Tele-MANAS on 14416" })).toHaveAttribute("href", "tel:14416");
});
