"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { WeeklySetup, weekdayName } from "@/components/WeeklySetup";
import { Dialog, useToast } from "@/components/ui/controls";
import { Button, Field, Notice, buttonClass } from "@/components/ui/primitives";
import { ApiError, api } from "@/lib/api";
import { WEEKLY_PURPOSE } from "@/lib/constants";
import { keys, useConsents, useErrorText } from "@/lib/hooks";
import { type Consent, type Contact, contactSchema, notificationSchema, page } from "@/lib/schemas";

function AddContact() {
  const t = useTranslations("sharing.contacts");
  const errorText = useErrorText();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ name: "", email: "", relationship: "" });
  const add = useMutation({
    mutationFn: () => api("/trusted-contacts", { method: "POST", body: form }),
    onSuccess: () => {
      setForm({ name: "", email: "", relationship: "" });
      void queryClient.invalidateQueries({ queryKey: keys.contacts });
      void queryClient.invalidateQueries({ queryKey: keys.notifications });
    },
  });
  const error = add.error instanceof ApiError ? add.error : null;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    add.mutate();
  };
  return (
    <form onSubmit={submit} noValidate className="space-y-4">
      <h3 className="font-medium">{t("add")}</h3>
      <Field
        label={t("name")}
        name="contact-name"
        autoComplete="off"
        maxLength={80}
        value={form.name}
        onChange={(event) => setForm({ ...form, name: event.target.value })}
        error={error?.field("name")}
      />
      <Field
        label={t("email")}
        name="contact-email"
        type="email"
        inputMode="email"
        autoComplete="off"
        value={form.email}
        onChange={(event) => setForm({ ...form, email: event.target.value })}
        error={error?.field("email")}
      />
      <Field
        label={t("relationship")}
        hint={t("relationshipHint")}
        name="contact-relationship"
        autoComplete="off"
        maxLength={40}
        value={form.relationship}
        onChange={(event) => setForm({ ...form, relationship: event.target.value })}
      />
      <p className="text-sm text-dim">{t("inviteNote")}</p>
      {error?.code === "display_name_required" ? (
        <Notice tone="attention" role="alert">
          <p>{t("needName")}</p>
          <Link href="/settings" className="link inline-flex min-h-11 items-center">
            {t("openSettings")}
          </Link>
        </Notice>
      ) : add.isError && !error?.field("name") && !error?.field("email") ? (
        <Notice tone="attention" role="alert">
          {errorText(add.error)}
        </Notice>
      ) : null}
      <Button type="submit" busy={add.isPending}>
        {t("invite")}
      </Button>
    </form>
  );
}

export default function SharingPage() {
  const t = useTranslations("sharing");
  const common = useTranslations("common");
  const format = useFormatter();
  const errorText = useErrorText();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [setupFor, setSetupFor] = useState<Contact | null>(null);
  const [removing, setRemoving] = useState<Contact | null>(null);

  const contacts = useQuery({
    queryKey: keys.contacts,
    queryFn: () => api("/trusted-contacts?page_size=20", { schema: page(contactSchema) }),
  });
  const consents = useConsents();
  const notifications = useQuery({
    queryKey: keys.notifications,
    queryFn: () => api("/notifications?page_size=20", { schema: page(notificationSchema) }),
  });
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: keys.contacts });
    void queryClient.invalidateQueries({ queryKey: keys.consents });
    void queryClient.invalidateQueries({ queryKey: keys.notifications });
  };

  const change = useMutation({
    mutationFn: ({ consent, action }: { consent: Consent; action: "pause" | "resume" | "confirm" | "stop" }) =>
      action === "stop"
        ? api(`/sharing/consent/${consent.id}`, { method: "DELETE" })
        : api(`/sharing/consent/${consent.id}/${action}`, { method: "POST" }),
    onSuccess: (_, { action }) => {
      toast(
        t(
          action === "pause"
            ? "weekly.paused_done"
            : action === "resume"
              ? "weekly.resumed_done"
              : action === "confirm"
                ? "weekly.confirmed_done"
                : "weekly.stopped_done",
        ),
      );
      refresh();
    },
    onError: (error) => toast(errorText(error)),
  });
  const resend = useMutation({
    mutationFn: (contact: Contact) =>
      api(`/trusted-contacts/${contact.id}/resend-invitation`, { method: "POST" }),
    onSuccess: refresh,
    onError: (error) => toast(errorText(error)),
  });
  const remove = useMutation({
    mutationFn: (contact: Contact) => api(`/trusted-contacts/${contact.id}`, { method: "DELETE" }),
    onSuccess: () => {
      setRemoving(null);
      refresh();
    },
  });

  const contactList = contacts.data?.results ?? [];
  const live = (consents.data?.results ?? []).filter(
    (consent) => consent.purpose === WEEKLY_PURPOSE && consent.status !== "revoked",
  );
  const activeCount = live.filter((consent) => consent.status === "active").length;
  const nameOf = (id: string | null) => contactList.find((contact) => contact.id === id)?.name ?? "";
  const withoutNote = contactList.filter(
    (contact) => contact.status === "confirmed" && !live.some((consent) => consent.contact === contact.id),
  );
  const when = (iso: string) => format.dateTime(new Date(iso), { dateStyle: "medium", timeStyle: "short" });
  const failed = contacts.isError || consents.isError;

  return (
    <div className="space-y-12">
      <div>
        <h1 className="h1 mb-4">{t("title")}</h1>
        <div className="mb-4">
          <Notice tone={activeCount > 0 ? "saved" : "info"} role="status">
            <span data-sharing-state={activeCount > 0 ? "on" : "off"}>
              {activeCount > 0 ? t("on", { count: activeCount }) : t("off")}
            </span>
          </Notice>
        </div>
        <p className="prose-width mb-2 text-dim">{t("intro")}</p>
        <p className="prose-width text-dim">{t("silence")}</p>
      </div>

      {failed ? (
        <Notice tone="attention" role="alert">
          <p>{t("error")}</p>
          <p className="text-dim">{errorText(contacts.error ?? consents.error)}</p>
          <button type="button" className="btn-text" onClick={refresh}>
            {common("tryAgain")}
          </button>
        </Notice>
      ) : null}

      <section aria-labelledby="weekly-title">
        <h2 id="weekly-title" className="h2 mb-3">
          {t("weekly.title")}
        </h2>
        {setupFor ? (
          <WeeklySetup contact={setupFor} onClose={() => setSetupFor(null)} />
        ) : (
          <>
            {live.length === 0 ? <p className="prose-width mb-4 text-dim">{t("weekly.none")}</p> : null}
            <ul className="space-y-4">
              {live.map((consent) => {
                const name = nameOf(consent.contact);
                return (
                  <li key={consent.id} className="frame p-5" data-consent={consent.status}>
                    <p className="mb-1 flex flex-wrap items-center gap-3 font-medium">
                      {t("weekly.to", { name })}
                      <span className="data text-dim">{t(`weekly.${consent.status === "active" ? "active" : "paused"}`)}</span>
                    </p>
                    <p className="text-dim">
                      {t("weekly.schedule", {
                        weekday: weekdayName(format, consent.send_weekday ?? 0),
                        hour: String(consent.send_hour ?? 9).padStart(2, "0"),
                      })}
                    </p>
                    {consent.next_send_at ? (
                      <p className="data text-dim">{t("weekly.next", { date: when(consent.next_send_at) })}</p>
                    ) : null}
                    {consent.status_reason === "reconfirmation_needed" ? (
                      <p className="mt-2 text-warm">{t("weekly.pausedReconfirm")}</p>
                    ) : null}
                    <div className="mt-4 flex flex-wrap gap-3">
                      {consent.status === "active" ? (
                        <Button
                          variant="quiet"
                          aria-label={t("weekly.pauseLabel", { name })}
                          onClick={() => change.mutate({ consent, action: "pause" })}
                        >
                          {t("weekly.pause")}
                        </Button>
                      ) : (
                        <Button
                          aria-label={t("weekly.resumeLabel", { name })}
                          onClick={() => change.mutate({ consent, action: "resume" })}
                        >
                          {t("weekly.resume")}
                        </Button>
                      )}
                      <Button
                        variant="quiet"
                        aria-label={t("weekly.stopLabel", { name })}
                        onClick={() => change.mutate({ consent, action: "stop" })}
                      >
                        {t("weekly.stop")}
                      </Button>
                      {consent.status === "active" ? (
                        <button
                          type="button"
                          className="btn-text"
                          onClick={() => change.mutate({ consent, action: "confirm" })}
                        >
                          {t("weekly.confirm")}
                        </button>
                      ) : null}
                    </div>
                  </li>
                );
              })}
            </ul>
            {withoutNote.length > 0 ? (
              <div className="mt-4 flex flex-col items-start gap-3">
                {withoutNote.map((contact) => (
                  <Button key={contact.id} variant="quiet" onClick={() => setSetupFor(contact)}>
                    {t("weekly.setUp", { name: contact.name })}
                  </Button>
                ))}
              </div>
            ) : null}
          </>
        )}
      </section>

      <section aria-labelledby="contacts-title">
        <h2 id="contacts-title" className="h2 mb-3">
          {t("contacts.title")}
        </h2>
        {contactList.length === 0 ? (
          <p className="prose-width mb-6 text-dim">{t("contacts.empty")}</p>
        ) : (
          <ul className="frame mb-6 divide-y divide-line">
            {contactList.map((contact) => (
              <li key={contact.id} className="p-5" data-contact={contact.status}>
                <p className="font-medium">
                  {contact.name} <span className="data text-dim">{contact.email}</span>
                </p>
                <p className="text-dim">{t(`contacts.status.${contact.status}`)}</p>
                <div className="mt-2 flex flex-wrap gap-x-5">
                  {contact.status === "pending" ? (
                    <button
                      type="button"
                      className="btn-text"
                      aria-label={t("contacts.resendLabel", { name: contact.name })}
                      onClick={() => resend.mutate(contact)}
                    >
                      {t("contacts.resend")}
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="btn-text"
                    aria-label={t("contacts.removeLabel", { name: contact.name })}
                    onClick={() => setRemoving(contact)}
                  >
                    {t("contacts.remove")}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
        {contactList.length < 3 ? <AddContact /> : null}
      </section>

      <section aria-labelledby="delivery-title">
        <h2 id="delivery-title" className="h2 mb-3">
          {t("delivery.title")}
        </h2>
        {notifications.data?.results.length ? (
          <>
            <ul className="frame mb-3 divide-y divide-line">
              {notifications.data.results.map((item) => (
                <li key={item.id} className="px-5 py-3" data-delivery={item.status}>
                  <p>
                    {t(`delivery.purpose.${item.purpose}`)}
                    {nameOf(item.contact) ? ` · ${nameOf(item.contact)}` : ""}
                  </p>
                  <p className="data text-dim">
                    {t(`delivery.status.${item.status}`)} · {when(item.sent_at ?? item.scheduled_at)}
                  </p>
                </li>
              ))}
            </ul>
            <p className="prose-width text-sm text-dim">{t("delivery.note")}</p>
          </>
        ) : (
          <p className="text-dim">{t("delivery.empty")}</p>
        )}
      </section>

      <Link href="/sharing/history" className={buttonClass("quiet")}>
        {t("history.link")}
      </Link>

      <Dialog
        open={removing !== null}
        onOpenChange={(open) => !open && setRemoving(null)}
        title={t("contacts.remove")}
        description={t("contacts.removeConfirm", { name: removing?.name ?? "" })}
      >
        <div className="flex flex-wrap gap-3">
          <Button variant="care" busy={remove.isPending} onClick={() => removing && remove.mutate(removing)}>
            {t("contacts.removeYes")}
          </Button>
          <Button variant="quiet" onClick={() => setRemoving(null)}>
            {t("contacts.removeNo")}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
