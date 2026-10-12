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

test.beforeAll(() => {
  // Placeholder knowledge, indexed because the development stack shows unreviewed content.
  manage(`
from django.core.management import call_command
call_command("seed_knowledge", verbosity=0)
call_command("index_knowledge", verbosity=0)
`);
});
test.beforeEach(() => resetThrottles());
test.afterAll(() => cleanUp());

function savedMessages(email: string): string {
  return lastLine(
    manage(`
from apps.chat.models import ChatMessage
print(ChatMessage.objects.filter(session__user__email=${JSON.stringify(email)}).count())
`),
  );
}

test("chat says it is an AI, answers from reviewed material, and shows its sources", async ({ page }) => {
  const problems = watchConsole(page);
  const email = createUser();
  await signIn(page, email);
  await page.goto("/chat");

  // The banner comes before any message.
  const banner = page.locator("[data-chat-banner]");
  await expect(banner.getByText("I am an AI, not a therapist, a counsellor or a doctor.")).toBeVisible();
  await expect(banner.getByText("I cannot diagnose, advise on medication or treatment")).toBeVisible();
  await expect(banner.getByText("Nobody monitors this chat")).toBeVisible();
  await expect(banner.getByText("Nothing you write here is saved unless you turn on saving.")).toBeVisible();
  await expect(banner.getByText("There is a daily limit on AI replies.")).toBeVisible();
  // Support never goes away.
  await expect(page.locator("[data-support-link]:visible")).toHaveCount(1);
  // Saving is off unless the person turns it on.
  await expect(page.getByRole("switch", { name: "Save this conversation" })).not.toBeChecked();
  await expectAccessible(page);

  await page.getByLabel("Your message").fill("How many hours of sleep do students usually need?");
  await page.getByRole("button", { name: "Send message" }).click();

  const answer = page.locator("[data-turn='answer']");
  await expect(answer).toContainText("AI reply");
  await expect(answer.locator("[data-sources]")).toContainText("Sleep basics for students");
  await expect(answer.getByRole("button", { name: "Mark this reply as helpful" })).toBeVisible();
  await answer.getByRole("button", { name: "Mark this reply as not helpful" }).click();
  await expect(answer.getByText("Thank you.")).toBeVisible();
  expect(savedMessages(email), "nothing is stored while saving is off").toBe("0");

  // Something outside the reviewed material gets a fixed reply, clearly labelled.
  await page.getByLabel("Your message").fill("What is the capital of France?");
  await page.getByRole("button", { name: "Send message" }).click();
  const fixed = page.locator("[data-turn='unsupported']");
  await expect(fixed).toContainText("Fixed reply, not written by AI");
  await expect(fixed).toContainText("I do not have reviewed material on that");
  await expectAccessible(page);
  expect(problems).toEqual([]);
});

test("a crisis message gets the fixed reply with routes the person chooses", async ({ page }) => {
  const email = createUser();
  await signIn(page, email);
  await page.goto("/chat");
  await page.getByLabel("Your message").fill("I don't want to live anymore");
  await page.getByRole("button", { name: "Send message" }).click();

  const reply = page.locator("[data-turn='safety']");
  await expect(reply).toContainText("Fixed reply, not written by AI");
  await expect(reply).toContainText("I am an AI");
  await expect(reply).toContainText("nobody is told about this conversation");
  await expect(reply).toContainText("call your local emergency number");
  for (const [name, href] of [
    ["Open Support", "/support"],
    ["My safety plan", "/support#plan"],
    ["Call a helpline", "/support#call"],
    ["Message a trusted person", "/support#message"],
  ] as const) {
    await expect(reply.getByRole("link", { name })).toHaveAttribute("href", href);
  }
  const text = (await reply.innerText()).toLowerCase();
  for (const claim of ["alerted", "notified", "monitoring", "on the way", "you are safe"]) {
    expect(text).not.toContain(claim);
  }
  // No feedback buttons and no sources on a fixed reply.
  await expect(reply.getByRole("button")).toHaveCount(0);
  await expectAccessible(page);

  // Nobody was contacted.
  const sent = lastLine(
    manage(`
from apps.notifications.models import Notification
print(Notification.objects.filter(user__email=${JSON.stringify(email)}).count())
`),
  );
  expect(sent).toBe("0");

  await reply.getByRole("link", { name: "Open Support" }).click();
  await expect(page).toHaveURL(/\/support$/);
});

test("saving is opt-in and can be deleted", async ({ page }) => {
  const email = createUser();
  await signIn(page, email);
  await page.goto("/chat");
  await page.getByRole("switch", { name: "Save this conversation" }).click();
  await expect(page.getByText("Saved to your account, encrypted, for 30 days.")).toBeVisible();

  await page.getByLabel("Your message").fill("Is there a breathing pattern that can steady me when tense?");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.locator("[data-turn='answer']")).toBeVisible();
  await expect.poll(() => savedMessages(email)).toBe("2");

  await page.getByRole("button", { name: "Delete the saved conversation" }).click();
  await expect(page.getByText("Saved conversation deleted.")).toBeVisible();
  await expect(page.locator("[data-turn]")).toHaveCount(0);
  await expect.poll(() => savedMessages(email)).toBe("0");
});

test("chat is accessible in the light theme and on desktop", async ({ page }) => {
  await setPrefs(page, { theme: "daybreak", motion: "reduced" });
  await signIn(page, createUser());
  await page.goto("/chat");
  await page.getByLabel("Your message").fill("I have exams and deadlines and feel stressed. One small step?");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.locator("[data-turn='answer']")).toBeVisible();
  await expectAccessible(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await expectAccessible(page);
});
