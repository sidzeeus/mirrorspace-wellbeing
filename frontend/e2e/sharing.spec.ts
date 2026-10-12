import { expect, test } from "@playwright/test";

import {
  PASSWORD,
  cleanUp,
  createContact,
  createUser,
  expectAccessible,
  lastLine,
  manage,
  resetThrottles,
  setPrefs,
  signIn,
  uniqueEmail,
} from "./helpers";

test.beforeEach(() => resetThrottles());
test.afterAll(() => cleanUp());

function invitationToken(contactEmail: string): string {
  return lastLine(
    manage(`
from apps.sharing.models import TrustedContact
from apps.sharing.tokens import make_token, INVITE
c = [c for c in TrustedContact.objects.all() if c.email == ${JSON.stringify(contactEmail)}][0]
print(make_token(c, INVITE))
`),
  );
}

function consentStatuses(email: string): string {
  return lastLine(
    manage(`
from apps.sharing.models import ConsentRecord
print(",".join(ConsentRecord.objects.filter(user__email=${JSON.stringify(email)}, purpose="weekly_summary").values_list("status", flat=True)))
`),
  );
}

test("sharing is off by default for a new account", async ({ page }) => {
  const email = createUser();
  await signIn(page, email);
  await page.goto("/sharing");

  await expect(page.locator("[data-sharing-state]")).toHaveAttribute("data-sharing-state", "off");
  await expect(page.getByText("Sharing is off. Nothing about you is sent to anyone.")).toBeVisible();
  await expect(page.getByText("No weekly note is set up.")).toBeVisible();
  await expect(page.getByText("Nobody added yet.")).toBeVisible();
  await expect(page.getByText("Nothing has been sent on your behalf.")).toBeVisible();
  await expect(page.locator("[data-consent]")).toHaveCount(0);
  expect(consentStatuses(email)).toBe("");
  await expectAccessible(page);
});

test("opt in, contact confirms, preview, confirm, pause, revoke", async ({ page, browser }) => {
  const email = createUser({ displayName: "Asha Rao" });
  const contactEmail = uniqueEmail("contact");
  await signIn(page, email);
  await page.goto("/sharing");

  // 1. Add a contact. They are invited and nothing more.
  await page.getByLabel("Their name").fill("Meera Iyer");
  await page.getByLabel("Their email").fill(contactEmail);
  await page.getByRole("button", { name: "Send invitation" }).click();
  const contactRow = page.locator("[data-contact]").filter({ hasText: "Meera Iyer" });
  await expect(contactRow).toHaveAttribute("data-contact", "pending");
  await expect(contactRow.getByText("Waiting for their answer")).toBeVisible();
  // No weekly note can be set up until they accept.
  await expect(page.getByRole("button", { name: /Set up a weekly note/ })).toHaveCount(0);

  // 2. The contact opens the link in their own browser and agrees.
  const contactContext = await browser.newContext();
  const contactPage = await contactContext.newPage();
  await contactPage.goto(`/contact-invitation#token=${invitationToken(contactEmail)}`);
  await expect(contactPage.getByText("Asha Rao would like to add you as a trusted contact.")).toBeVisible();
  await expect(contactPage.getByText("not monitored")).toBeVisible();
  await expectAccessible(contactPage);
  await contactPage.getByRole("button", { name: "I agree to receive these" }).click();
  await expect(contactPage.getByText("You have agreed.")).toBeVisible();
  await contactContext.close();

  // 3. Status is visible to the student.
  await page.reload();
  await expect(page.locator("[data-contact]").filter({ hasText: "Meera Iyer" })).toHaveAttribute(
    "data-contact",
    "confirmed",
  );

  // 4. Step by step: what is shared, the real message, then confirm.
  await page.getByRole("button", { name: "Set up a weekly note for Meera Iyer" }).click();
  const setup = page.locator("[data-weekly-setup]");
  await expect(setup.getByText("Step 1 of 3")).toBeVisible();
  await expect(setup.locator("[data-notice='shared'] li")).toHaveText([
    "Your display name",
    "The dates of the week covered",
    "How many of those 7 days you checked in",
    "One fixed line that is the same for everyone",
  ]);
  await expect(setup.locator("[data-notice='neverShared']")).toContainText("Mood, sleep, energy or stress values");
  await expectAccessible(page);
  await setup.getByRole("button", { name: "Continue" }).click();

  await expect(setup.getByText("Step 2 of 3")).toBeVisible();
  await expect(setup.locator("[data-preview-recipient]")).toHaveText(`Meera Iyer (${contactEmail})`);
  const body = await setup.locator("[data-preview-body]").innerText();
  expect(body).toContain("Asha Rao uses Mirrorspace");
  expect(body).toMatch(/checked in \d of 7 days\./);
  expect(body).toContain("Silence does not mean anything either way.");
  for (const word of ["mood", "sleep", "stress", "energy"]) expect(body.toLowerCase()).not.toContain(word);
  await setup.getByRole("button", { name: "Continue" }).click();

  await expect(setup.getByText("Step 3 of 3")).toBeVisible();
  await setup.getByRole("button", { name: "Turn on weekly note" }).click();
  await expect(setup.getByText("Tick the box to turn the weekly note on.")).toBeVisible();
  expect(consentStatuses(email), "nothing is on before the explicit confirmation").toBe("");
  await setup.getByLabel("Day").selectOption({ label: "Wednesday" });
  await setup.getByLabel(/Send this note to Meera Iyer every week/).check();
  await expectAccessible(page);
  await setup.getByRole("button", { name: "Turn on weekly note" }).click();

  // 5. The schedule is visible.
  const consent = page.locator("[data-consent]");
  await expect(consent).toHaveAttribute("data-consent", "active");
  await expect(consent.getByText("Every Wednesday at 09:00, your time")).toBeVisible();
  await expect(consent.getByText(/Next note:/)).toBeVisible();
  await expect(page.locator("[data-sharing-state]")).toHaveAttribute("data-sharing-state", "on");
  await expect(page.getByText("does not mean anything about your safety")).toBeVisible();

  // 6. Pause is one tap; so is stopping.
  await page.getByRole("button", { name: "Pause the weekly note to Meera Iyer" }).click();
  await expect(consent).toHaveAttribute("data-consent", "paused");
  await expect(page.locator("[data-sharing-state]")).toHaveAttribute("data-sharing-state", "off");
  await page.getByRole("button", { name: "Resume the weekly note to Meera Iyer" }).click();
  await expect(consent).toHaveAttribute("data-consent", "active");
  await page.getByRole("button", { name: "Stop the weekly note to Meera Iyer" }).click();
  await expect(page.locator("[data-consent]")).toHaveCount(0);
  await expect(page.getByText("Sharing is off.")).toBeVisible();
  expect(consentStatuses(email)).toBe("revoked");

  // 7. Delivery status and the consent history remain visible.
  await expect(page.locator("[data-delivery]").filter({ hasText: "Invitation" })).toBeVisible();
  await page.getByRole("link", { name: "Consent history" }).click();
  const withdrawn = page.locator("[data-history='revoked']");
  await expect(withdrawn).toContainText("Weekly note");
  await expect(withdrawn).toContainText("Agreed on");
  await expect(withdrawn).toContainText("Withdrawn on");
  await expect(withdrawn).toContainText("Notice version 2026-10-placeholder-1");
  await expect(page.locator("[data-history]").filter({ hasText: "Privacy and safety notice" })).toBeVisible();
  await expectAccessible(page);
});

test("a contact can decline, and can unsubscribe from any email", async ({ page }) => {
  const email = createUser();
  const declining = uniqueEmail("decline");
  createContact(email, { name: "Dev", contactEmail: declining, status: "pending" });
  await page.goto(`/contact-invitation#token=${invitationToken(declining)}`);
  await page.getByRole("button", { name: "No, thank you" }).click();
  await expect(page.getByText("You have declined.")).toBeVisible();

  const leaving = uniqueEmail("leave");
  createContact(email, { name: "Lee", contactEmail: leaving });
  const token = lastLine(
    manage(`
from apps.sharing.models import TrustedContact
from apps.sharing.tokens import make_token, UNSUBSCRIBE
c = [c for c in TrustedContact.objects.all() if c.email == ${JSON.stringify(leaving)}][0]
print(make_token(c, UNSUBSCRIBE))
`),
  );
  await page.goto(`/unsubscribe#token=${token}`);
  await expectAccessible(page);
  await page.getByRole("button", { name: "Unsubscribe" }).click();
  await expect(page.getByText("You are unsubscribed.")).toBeVisible();

  await page.goto("/contact-invitation#token=forged");
  await expect(page.getByText("This link is not valid or has expired.")).toBeVisible();
});

test("adding a contact needs a display name first", async ({ page }) => {
  await signIn(page, createUser({ displayName: "" }));
  await page.goto("/sharing");
  await page.getByLabel("Their name").fill("Meera");
  await page.getByLabel("Their email").fill(uniqueEmail("c"));
  await page.getByRole("button", { name: "Send invitation" }).click();
  await expect(page.getByText("Add your display name in Settings first")).toBeVisible();
  await page.getByRole("link", { name: "Open Settings" }).click();
  await expect(page).toHaveURL(/\/settings$/);
});

test("settings: comfort controls, export and account deletion", async ({ page }) => {
  const email = createUser();
  await signIn(page, email);
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Settings and privacy" })).toBeVisible();
  await expectAccessible(page);

  await page.getByLabel("Theme").selectOption("daybreak");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "daybreak");
  await expectAccessible(page);
  await page.getByRole("switch", { name: "Larger text" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-text", "large");
  await page.getByRole("switch", { name: "Reduce motion" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-motion", "reduced");
  await page.getByRole("switch", { name: "Low-bandwidth mode" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-bandwidth", "low");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "daybreak");
  await expect(page.locator("html")).toHaveAttribute("data-text", "large");

  await page.getByLabel("Display name").fill("Asha R");
  await page.getByLabel("Time zone").fill("Not/AZone");
  await page.getByRole("button", { name: "Save account details" }).click();
  await expect(page.getByText("Choose a valid time zone")).toBeVisible();
  await page.getByLabel("Time zone").fill("Asia/Kolkata");
  await page.getByRole("button", { name: "Save account details" }).click();
  await expect(page.getByText("Saved.", { exact: true })).toBeVisible();

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download my data" }).click();
  const file = await download;
  expect(file.suggestedFilename()).toBe("my-data.json");
  const exported = JSON.parse(await (await file.createReadStream()).toArray().then((chunks) => Buffer.concat(chunks).toString()));
  expect(exported.account.email).toBe(email);
  expect(Object.keys(exported)).toEqual(
    expect.arrayContaining(["check_ins", "episodes", "safety_plan", "trusted_contacts", "consents"]),
  );

  // Deleting says plainly what goes and what stays, and needs the password.
  await page.getByRole("button", { name: "Delete my account" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("Deleted for good: your account, check-ins")).toBeVisible();
  await expect(dialog.getByText("Kept for up to 12 months, with nothing that identifies you")).toBeVisible();
  await expectAccessible(page);
  await expect(dialog.getByRole("button", { name: "Delete my account for good" })).toBeDisabled();
  await dialog.getByLabel("Enter your password to confirm").fill("wrong-password");
  await dialog.getByRole("button", { name: "Delete my account for good" }).click();
  await expect(dialog.getByText("That password is incorrect.")).toBeVisible();
  await dialog.getByLabel("Enter your password to confirm").fill(PASSWORD);
  await dialog.getByRole("button", { name: "Delete my account for good" }).click();
  await expect(page).toHaveURL(/\/$/);

  const remaining = lastLine(
    manage(`
from apps.accounts.models import User
print(User.objects.filter(email=${JSON.stringify(email)}).count())
`),
  );
  expect(remaining).toBe("0");
});

for (const theme of ["night", "daybreak"] as const) {
  test(`sharing with an active note is accessible in ${theme}`, async ({ page }) => {
    await setPrefs(page, { theme, motion: "reduced" });
    const email = createUser();
    createContact(email, { name: "Meera Iyer", contactEmail: uniqueEmail("a11y") });
    manage(`
from apps.accounts.models import User
from apps.sharing.models import TrustedContact
from apps.sharing.services import grant_weekly_consent
from apps.sharing.notices import WEEKLY_NOTICE_VERSION
from apps.sharing.weekly import weekly_format_hash
u = User.objects.get(email=${JSON.stringify(email)})
grant_weekly_consent(u, TrustedContact.objects.get(user=u), notice_version=WEEKLY_NOTICE_VERSION, preview_hash=weekly_format_hash())
`);
    await signIn(page, email);
    await page.goto("/sharing");
    await expect(page.locator("[data-consent='active']")).toBeVisible();
    await expectAccessible(page);
    await page.setViewportSize({ width: 1440, height: 900 });
    await expectAccessible(page);
  });
}
