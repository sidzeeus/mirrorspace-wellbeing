"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { SignOut } from "@/components/AppShell";
import { PreferenceControls } from "@/components/PreferenceControls";
import { Dialog, useToast } from "@/components/ui/controls";
import { Button, Field, Notice, buttonClass } from "@/components/ui/primitives";
import { ApiError, api, forgetCsrfToken } from "@/lib/api";
import { keys, useErrorText, useMe } from "@/lib/hooks";
import { clearOfflineCopies } from "@/lib/offline";
import { type Me, meSchema } from "@/lib/schemas";

function AccountForm({ me }: { me: Me }) {
  const t = useTranslations("settings");
  const errorText = useErrorText();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [displayName, setDisplayName] = useState(me.display_name);
  const [timezone, setTimezone] = useState(me.timezone);
  const save = useMutation({
    mutationFn: () =>
      api("/auth/me", {
        method: "PATCH",
        body: { display_name: displayName.trim(), timezone: timezone.trim() },
        schema: meSchema,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(keys.me, updated);
      toast(t("saved"));
    },
  });
  const error = save.error instanceof ApiError ? save.error : null;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    save.mutate();
  };
  return (
    <form onSubmit={submit} noValidate className="space-y-5">
      <Field
        label={t("displayName")}
        hint={t("displayNameHint")}
        name="display_name"
        maxLength={60}
        autoComplete="nickname"
        value={displayName}
        onChange={(event) => setDisplayName(event.target.value)}
        error={error?.field("display_name")}
      />
      <Field
        label={t("timezone")}
        hint={t("timezoneHint")}
        name="timezone"
        autoComplete="off"
        value={timezone}
        onChange={(event) => setTimezone(event.target.value)}
        error={error?.field("timezone")}
      />
      {save.isError && !error?.field("timezone") && !error?.field("display_name") ? (
        <Notice tone="attention" role="alert">
          {errorText(save.error)}
        </Notice>
      ) : null}
      <Button type="submit" variant="quiet" busy={save.isPending}>
        {t("saveAccount")}
      </Button>
    </form>
  );
}

export default function SettingsPage() {
  const t = useTranslations("settings");
  const shell = useTranslations("shell");
  const errorText = useErrorText();
  const toast = useToast();
  const queryClient = useQueryClient();
  const me = useMe();
  const [deleting, setDeleting] = useState(false);
  const [password, setPassword] = useState("");

  const exportData = useMutation({
    mutationFn: async () => {
      const data = await api("/export");
      // Built in the browser and handed straight to the download; nothing is kept.
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = "my-data.json";
      link.click();
      URL.revokeObjectURL(url);
    },
    onSuccess: () => toast(t("exportDone")),
    onError: (error) => toast(errorText(error)),
  });

  const deleteAccount = useMutation({
    mutationFn: () => api("/account", { method: "DELETE", body: { password } }),
    onSuccess: () => {
      clearOfflineCopies();
      forgetCsrfToken();
      queryClient.clear();
      // A full page load, on purpose: it drops everything held in memory.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign("/");
    },
  });

  return (
    <div className="space-y-12">
      <h1 className="h1">{t("title")}</h1>

      <section aria-labelledby="comfort-title">
        <h2 id="comfort-title" className="h2 mb-4">
          {t("comfort")}
        </h2>
        <PreferenceControls />
      </section>

      <section aria-labelledby="account-title">
        <h2 id="account-title" className="h2 mb-4">
          {t("account")}
        </h2>
        {me.data ? <AccountForm key={me.data.id} me={me.data} /> : null}
      </section>

      <section aria-labelledby="signout-title">
        <h2 id="signout-title" className="h2 mb-4">
          {shell("signOut")}
        </h2>
        {me.data ? <p className="mb-3 text-sm text-dim">{shell("signedInAs", { email: me.data.email })}</p> : null}
        <SignOut />
      </section>

      <section aria-labelledby="data-title">
        <h2 id="data-title" className="h2 mb-4">
          {t("data")}
        </h2>
        <div className="space-y-5">
          <div>
            <Button variant="quiet" busy={exportData.isPending} onClick={() => exportData.mutate()}>
              {t("export")}
            </Button>
            <p className="mt-1 text-sm text-dim">{t("exportHint")}</p>
          </div>
          <div>
            <Link href="/sharing/history" className={buttonClass("quiet")}>
              {t("consentHistory")}
            </Link>
            <p className="mt-1 text-sm text-dim">{t("consentHistoryHint")}</p>
          </div>
        </div>
      </section>

      <section aria-labelledby="delete-title">
        <h2 id="delete-title" className="h2 mb-4">
          {t("delete.title")}
        </h2>
        <Button variant="quiet" onClick={() => setDeleting(true)}>
          {t("delete.open")}
        </Button>
      </section>

      <Dialog
        open={deleting}
        onOpenChange={(open) => {
          setDeleting(open);
          if (!open) setPassword("");
        }}
        title={t("delete.title")}
        description={t("delete.intro")}
      >
        <form
          noValidate
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            deleteAccount.mutate();
          }}
        >
          <p>{t("delete.removed")}</p>
          <p className="text-dim">{t("delete.kept")}</p>
          <p className="text-dim">{t("delete.contacts")}</p>
          <Field
            label={t("delete.password")}
            name="delete-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            error={deleteAccount.isError ? errorText(deleteAccount.error) : undefined}
          />
          <div className="flex flex-wrap gap-3">
            <Button type="submit" variant="care" busy={deleteAccount.isPending} disabled={!password}>
              {t("delete.confirm")}
            </Button>
            <Button variant="quiet" onClick={() => setDeleting(false)}>
              {t("delete.keep")}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
