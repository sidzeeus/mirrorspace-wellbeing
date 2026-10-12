"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { useState, useSyncExternalStore } from "react";

import { BreathingPlayer } from "@/components/BreathingPlayer";
import { ResourceList } from "@/components/ResourceList";
import { Button, Notice, Panel, buttonClass } from "@/components/ui/primitives";
import { ApiError, api } from "@/lib/api";
import { useErrorText, useMe } from "@/lib/hooks";
import { useOfflinePlan, useOfflineResources } from "@/lib/offline";
import { type Contact, type SosPreview, contactSchema, page, sosPreviewSchema } from "@/lib/schemas";

const OPTIONS = ["calm", "plan", "message", "call"] as const;
const PLAN_SECTIONS = ["warning_signs", "coping_steps", "people"] as const;

const subscribeOnline = (listener: () => void) => {
  window.addEventListener("online", listener);
  window.addEventListener("offline", listener);
  return () => {
    window.removeEventListener("online", listener);
    window.removeEventListener("offline", listener);
  };
};

/** The message flow: choose a person, see exactly what will be sent, then confirm. */
function MessageTrustedPerson({ signedIn, online }: { signedIn: boolean; online: boolean }) {
  const t = useTranslations("support.message");
  const errorText = useErrorText();
  const [review, setReview] = useState<{ preview: SosPreview; key: string } | null>(null);
  const [cancelled, setCancelled] = useState(false);

  const contacts = useQuery({
    queryKey: ["support", "contacts"],
    queryFn: async () =>
      (await api("/trusted-contacts?page_size=20", { schema: page(contactSchema) })).results.filter(
        (contact) => contact.status === "confirmed",
      ),
    enabled: signedIn && online,
    retry: false,
  });
  const preview = useMutation({
    mutationFn: (contact: Contact) =>
      api("/sos/preview", { method: "POST", body: { contact: contact.id }, schema: sosPreviewSchema }),
    onSuccess: (data) => {
      setCancelled(false);
      // One key per review: a double tap or a retry can only ever send one message.
      setReview({ preview: data, key: crypto.randomUUID() });
    },
  });
  const send = useMutation({
    mutationFn: () =>
      api("/sos/notify-contact", {
        method: "POST",
        body: {
          contact: review?.preview.recipient.id,
          message_hash: review?.preview.message_hash,
          idempotency_key: review?.key,
          confirmed: true,
        },
      }) as Promise<{ detail: string }>,
  });

  if (!online) return <Notice tone="attention">{t("needsConnection")}</Notice>;
  if (!signedIn) {
    return (
      <p>
        <Link href="/login" className="link inline-flex min-h-11 items-center">
          {t("signIn")}
        </Link>
      </p>
    );
  }

  if (send.isSuccess) {
    return (
      <div role="status">
        <h3 className="h2 mb-2">{t("queuedTitle")}</h3>
        {/* The API's own words: it says "queued", never "delivered" or "read". */}
        <p className="mb-2">{send.data.detail}</p>
        <p className="text-dim">{t("status")}</p>
        <a href="#menu" className={`${buttonClass("quiet")} mt-4`}>
          {t("another")}
        </a>
      </div>
    );
  }

  if (review) {
    const { recipient, subject, body, recipient_can_receive: canReceive } = review.preview;
    return (
      <Panel marks className="p-5" data-sos-review>
        <h3 className="h2 mb-4">{t("reviewTitle")}</h3>
        <dl className="mb-5 space-y-3">
          <div>
            <dt className="text-sm text-dim">{t("to")}</dt>
            <dd className="font-medium" data-sos-recipient>
              {recipient.name} <span className="data text-dim">({recipient.email})</span>
            </dd>
          </div>
          <div>
            <dt className="text-sm text-dim">{t("subject")}</dt>
            <dd>{subject}</dd>
          </div>
          <div>
            <dt className="text-sm text-dim">{t("text")}</dt>
            <dd className="whitespace-pre-wrap" data-sos-body>
              {body}
            </dd>
          </div>
        </dl>
        {!canReceive ? (
          <Notice tone="attention" role="alert">
            {t("notReceiving")}
          </Notice>
        ) : null}
        {send.isError ? (
          <div className="mb-3">
            <Notice tone="attention" role="alert">
              {errorText(send.error)}
            </Notice>
          </div>
        ) : null}
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <Button variant="care" busy={send.isPending} disabled={!canReceive} onClick={() => send.mutate()}>
            {send.isPending ? t("sending") : t("send")}
          </Button>
          <Button
            variant="quiet"
            onClick={() => {
              setReview(null);
              setCancelled(true);
            }}
          >
            {t("cancel")}
          </Button>
        </div>
      </Panel>
    );
  }

  return (
    <div>
      <p className="prose-width mb-4 text-dim">{t("intro")}</p>
      {cancelled ? (
        <div className="mb-4">
          <Notice role="status">{t("cancelled")}</Notice>
        </div>
      ) : null}
      {preview.isError ? (
        <div className="mb-4">
          <Notice tone="attention" role="alert">
            {errorText(preview.error)}
          </Notice>
        </div>
      ) : null}
      {contacts.isError ? (
        <Notice tone="attention" role="alert">
          {contacts.error instanceof ApiError && contacts.error.status === 401
            ? t("signIn")
            : errorText(contacts.error)}
        </Notice>
      ) : contacts.data?.length ? (
        <ul className="space-y-3">
          {contacts.data.map((contact) => (
            <li key={contact.id}>
              <Button variant="quiet" className="w-full" onClick={() => preview.mutate(contact)}>
                {t("choose", { name: contact.name })}
              </Button>
            </li>
          ))}
        </ul>
      ) : contacts.isPending ? null : (
        <div>
          <p className="mb-3 text-dim">{t("none")}</p>
          <Link href="/sharing" className={buttonClass("quiet")}>
            {t("setUp")}
          </Link>
        </div>
      )}
    </div>
  );
}

/**
 * Support (SOS). One calm page with four options, each a section further down, so it
 * works with a keyboard, a screen reader, no JavaScript, and no connection. Nothing on
 * this page moves unless the person starts the breathing aid themselves.
 */
export default function SupportPage() {
  const t = useTranslations("support");
  const format = useFormatter();
  const online = useSyncExternalStore(
    subscribeOnline,
    () => navigator.onLine,
    () => true,
  );
  const me = useMe();
  const signedIn = Boolean(me.data);
  const plan = useOfflinePlan(signedIn || !online || me.isError);
  const resources = useOfflineResources();
  const [breathing, setBreathing] = useState(false);
  const date = (iso: string) => format.dateTime(new Date(iso), { dateStyle: "medium" });
  const planData = plan.data?.data;
  const planEmpty = planData ? PLAN_SECTIONS.every((section) => planData[section].length === 0) : false;

  return (
    <div className="mx-auto min-h-dvh max-w-2xl px-5 pb-16" data-support-screen>
      <header className="flex h-16 items-center justify-between">
        <h1 className="h2">{t("title")}</h1>
        <a href="/home" className={buttonClass("quiet")}>
          {t("close")}
        </a>
      </header>

      <main id="main" className="space-y-12">
        <div className="space-y-3">
          <p className="text-lg">{t("intro")}</p>
          <p className="prose-width text-dim">{t("limits")}</p>
          <Notice tone="attention">{t("emergency")}</Notice>
          {online ? null : (
            <Notice tone="attention" role="status">
              {t("offline")}
            </Notice>
          )}
        </div>

        <nav id="menu" aria-label={t("menu")}>
          <ul className="grid gap-3 sm:grid-cols-2">
            {OPTIONS.map((option) => (
              <li key={option}>
                <a
                  href={`#${option}`}
                  className="frame block min-h-24 p-5 hover:bg-raised"
                  data-support-option={option}
                >
                  <span className="block text-lg font-medium">{t(`options.${option}`)}</span>
                  <span className="block text-dim">{t(`options.${option}Hint`)}</span>
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <section id="calm" aria-labelledby="calm-title" className="scroll-mt-6">
          <h2 id="calm-title" className="h1 mb-3">
            {t("calm.title")}
          </h2>
          <p className="mb-5 text-dim">{t("calm.body")}</p>
          {/* Mounted only on request, so nothing on this screen moves by itself. */}
          {breathing ? (
            <BreathingPlayer inhale={4} exhale={6} minutes={3} onFinish={() => setBreathing(false)} />
          ) : (
            <Button variant="quiet" onClick={() => setBreathing(true)}>
              {t("options.calm")}
            </Button>
          )}
        </section>

        <section id="plan" aria-labelledby="plan-title" className="scroll-mt-6">
          <h2 id="plan-title" className="h1 mb-3">
            {t("plan.title")}
          </h2>
          {planData && !planEmpty ? (
            <>
              {plan.data?.savedAt ? (
                <p className="data mb-3 text-dim">{t("plan.saved", { date: date(plan.data.savedAt) })}</p>
              ) : null}
              <div className="frame divide-y divide-line">
                {PLAN_SECTIONS.filter((section) => planData[section].length > 0).map((section) => (
                  <div key={section} className="p-5">
                    <h3 className="mb-2 font-medium">{t(`plan.${section}`)}</h3>
                    <ul className="list-disc space-y-1 pl-5">
                      {planData[section].map((line, index) => (
                        <li key={index}>{line}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
              <Link href="/plan" className={`${buttonClass("quiet")} mt-4`}>
                {t("plan.edit")}
              </Link>
            </>
          ) : planData ? (
            <>
              <p className="mb-4 text-dim">{t("plan.empty")}</p>
              <Link href="/plan" className={buttonClass("quiet")}>
                {t("plan.write")}
              </Link>
            </>
          ) : plan.isError && plan.error instanceof ApiError && plan.error.status !== 401 ? (
            <Notice tone="attention">{t("plan.unavailable")}</Notice>
          ) : plan.isFetching ? null : (
            <Link href="/login" className="link inline-flex min-h-11 items-center">
              {t("plan.signIn")}
            </Link>
          )}
        </section>

        <section id="message" aria-labelledby="message-title" className="scroll-mt-6">
          <h2 id="message-title" className="h1 mb-3">
            {t("message.title")}
          </h2>
          <MessageTrustedPerson signedIn={signedIn} online={online} />
        </section>

        <section id="call" aria-labelledby="call-title" className="scroll-mt-6">
          <h2 id="call-title" className="h1 mb-3">
            {t("call.title")}
          </h2>
          {resources.data ? (
            <>
              {resources.data.savedAt ? (
                <p className="data mb-3 text-dim">{t("call.saved", { date: date(resources.data.savedAt) })}</p>
              ) : null}
              {resources.data.data.length > 0 ? (
                <ResourceList resources={resources.data.data} />
              ) : (
                <p className="text-dim">{t("call.empty")}</p>
              )}
            </>
          ) : resources.isError ? (
            <Notice tone="attention">{t("call.unavailable")}</Notice>
          ) : null}
        </section>

        <a href="#menu" className="link inline-flex min-h-11 items-center">
          {t("top")}
        </a>
      </main>
    </div>
  );
}
