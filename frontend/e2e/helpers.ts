import { execFileSync } from "node:child_process";
import path from "node:path";

import AxeBuilder from "@axe-core/playwright";
import { type Page, expect } from "@playwright/test";

const REPO_ROOT = path.resolve(__dirname, "..", "..");
export const PASSWORD = "correct-horse-battery-staple";

/** Run Python inside the API container. Used only to set up and inspect test data. */
export function manage(code: string): string {
  return execFileSync(
    "docker",
    ["compose", "exec", "-T", "web", "python", "manage.py", "shell", "-c", code],
    { cwd: REPO_ROOT, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] },
  ).trim();
}

let counter = 0;
export function uniqueEmail(prefix = "e2e"): string {
  counter += 1;
  return `${prefix}.${Date.now()}.${counter}@e2e.test`;
}

type UserOptions = { displayName?: string; onboarded?: boolean };

/** A verified account that has already accepted the notice, unless told otherwise. */
export function createUser({ displayName = "Asha Rao", onboarded = true }: UserOptions = {}): string {
  const email = uniqueEmail();
  manage(`
from django.utils import timezone
from apps.accounts.models import User
from apps.sharing.services import record_privacy_notice
from apps.sharing.notices import PRIVACY_NOTICE_VERSION
u = User.objects.create_user(${JSON.stringify(email)}, ${JSON.stringify(PASSWORD)}, email_verified_at=timezone.now(), age_confirmed_at=timezone.now(), display_name=${JSON.stringify(displayName)})
${onboarded ? "record_privacy_notice(u, PRIVACY_NOTICE_VERSION)" : ""}
`);
  return email;
}

export function verificationToken(email: string): string {
  return manage(`
from apps.accounts.models import User
from apps.accounts.tokens import make_email_verification_token
print(make_email_verification_token(User.objects.get(email=${JSON.stringify(email)})))
`);
}

/** Remove every account the browser tests created. */
export function cleanUp(): void {
  manage(`
from apps.accounts.models import User
from apps.accounts import services
for u in User.objects.filter(email__endswith="@e2e.test"):
    services._erase(u)
from django.core.cache import cache
cache.clear()
`);
}

/** Clear rate-limit counters so a long test run is not throttled. */
export function resetThrottles(): void {
  manage("from django.core.cache import cache; cache.clear()");
}

export async function signIn(page: Page, email: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/(home|onboarding)/);
}

/** No accessibility violations at WCAG 2.2 AA, as far as automated checks can tell. */
export async function expectAccessible(page: Page): Promise<void> {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  const summary = results.violations.map(
    (violation) =>
      `${violation.id}: ${violation.help} -> ${violation.nodes
        .slice(0, 3)
        .map((node) => node.target.join(" "))
        .join(" | ")}`,
  );
  expect(summary, `on ${page.url()}`).toEqual([]);
}

export async function setPrefs(page: Page, prefs: Record<string, string>): Promise<void> {
  await page.addInitScript((value) => {
    window.localStorage.setItem("prefs", JSON.stringify(value));
  }, prefs);
}

/** Collect console errors and failed requests so a test can assert there were none. */
export function watchConsole(page: Page): string[] {
  const problems: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") problems.push(message.text());
  });
  page.on("pageerror", (error) => problems.push(error.message));
  return problems;
}
