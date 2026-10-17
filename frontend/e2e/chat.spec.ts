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

  // One line says it is an AI before any message; the full disclosure is one tap away.
  const banner = page.locator("[data-chat-banner]");
  await expect(banner).toContainText("Mira is an AI, not a therapist. Nobody monitors this chat.");
  await banner.getByRole("button", { name: "About this chat" }).click();
  await expect(banner.getByText("I am an AI, not a therapist, a counsellor or a doctor.")).toBeVisible();
  await expect(banner.getByText("I cannot diagnose, advise on medication or treatment")).toBeVisible();
  await expect(banner.locator("dd").getByText("Nobody monitors this chat")).toBeVisible();
  await expect(banner.getByText("Nothing you write here is saved unless you turn on saving.")).toBeVisible();
  await expect(banner.getByText("There is a daily limit on AI replies.")).toBeVisible();
  // Support never goes away.
  await expect(page.locator("[data-support-link]:visible")).toHaveCount(1);
  // Saving is off unless the person turns it on.
  await page.getByRole("button", { name: "Chat settings" }).click();
  await expect(page.getByRole("switch", { name: "Save this conversation" })).not.toBeChecked();
  await expectAccessible(page);

  await page.getByLabel("Your message").fill("How many hours of sleep do students usually need?");
  await page.getByRole("button", { name: "Send message" }).click();

  // A real local model can take a while, especially the first reply.
  const answer = page.locator("[data-turn='answer']").first();
  await expect(answer).toContainText("AI reply", { timeout: 90_000 });
  await expect(answer.locator("[data-sources]")).toContainText("Sleep basics for students");
  await expect(answer.getByRole("button", { name: "Mark this reply as helpful" })).toBeVisible();
  await answer.getByRole("button", { name: "Mark this reply as not helpful" }).click();
  await expect(answer.getByText("Thank you.")).toBeVisible();
  expect(savedMessages(email), "nothing is stored while saving is off").toBe("0");

  // Ordinary conversation outside the reviewed material is answered by the AI too.
  await page.getByLabel("Your message").fill("hey, how are you doing?");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.locator("[data-turn='answer']")).toHaveCount(2, { timeout: 90_000 });
  await expect(page.locator("[data-turn='answer']").last()).toContainText("AI reply");
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
  await page.getByRole("button", { name: "Chat settings" }).click();
  await page.getByRole("switch", { name: "Save this conversation" }).click();
  await expect(page.getByText("Saved to your account, encrypted, for 30 days.")).toBeVisible();

  await page.getByLabel("Your message").fill("Is there a breathing pattern that can steady me when tense?");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.locator("[data-turn='answer']")).toBeVisible();
  await expect.poll(() => savedMessages(email)).toBe("2");

  await page.getByRole("button", { name: "Delete the saved conversation" }).click();
  await expect(page.getByText("Saved conversation deleted.", { exact: true })).toBeVisible();
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

test("voice: Talk sends what was said, and the reply is read aloud", async ({ page }) => {
  // A stand-in microphone and speaker: the browser's speech services are not available
  // to automated tests, so these play their part.
  await page.addInitScript(() => {
    const scope = window as unknown as Record<string, unknown>;
    scope.__spoken = [] as string[];
    class FakeRecognition {
      lang = "";
      interimResults = false;
      continuous = false;
      onresult: ((event: unknown) => void) | null = null;
      onerror: ((event: unknown) => void) | null = null;
      onend: (() => void) | null = null;
      start() {
        setTimeout(() => {
          const said = "How many hours of sleep do students usually need?";
          this.onresult?.({ resultIndex: 0, results: [{ isFinal: true, 0: { transcript: said } }] });
          this.onend?.();
        }, 300);
      }
      stop() {}
      abort() {}
    }
    // Newer browsers have the unprefixed name, older ones only the prefixed one.
    scope.SpeechRecognition = FakeRecognition;
    scope.webkitSpeechRecognition = FakeRecognition;
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: {
        speak: (utterance: { text: string }) => (scope.__spoken as string[]).push(utterance.text),
        cancel: () => undefined,
        getVoices: () => [],
      },
    });
  });
  await signIn(page, createUser());
  await page.goto("/chat");

  await page.getByRole("button", { name: "Chat settings" }).click();
  await expect(page.locator("[data-voice-settings]")).toContainText("This app never records or keeps audio");
  await page.locator("[data-voice-talk]").click();
  const answer = page.locator("[data-turn='answer']").first();
  await expect(answer).toContainText("AI reply", { timeout: 90_000 });
  await expect(page.locator("[data-turn='user']")).toContainText("How many hours of sleep");
  await expect
    .poll(() => page.evaluate(() => ((window as unknown as Record<string, string[]>).__spoken ?? []).join(" ")))
    .not.toBe("");
  await expectAccessible(page);
});

test("Enter sends a message and Shift+Enter starts a new line", async ({ page }) => {
  await signIn(page, createUser());
  await page.goto("/chat");
  await expect(page.getByText("Hi, I'm Mira.")).toBeVisible();
  const box = page.getByLabel("Your message");
  await box.fill("first line");
  await box.press("Shift+Enter");
  await box.pressSequentially("second line");
  await expect(box).toHaveValue(/^first line\nsecond line$/);
  await box.press("Enter");
  await expect(box).toHaveValue("");
  await expect(page.locator("[data-turn='user']")).toContainText("second line");
  await expect(page.locator("[data-turn='answer']").first()).toBeVisible({ timeout: 90_000 });
});
