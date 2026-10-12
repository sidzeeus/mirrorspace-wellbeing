"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { type FormEvent, useId, useRef, useState } from "react";
import { z } from "zod";

import { Toggle, useToast } from "@/components/ui/controls";
import { Button, Notice, buttonClass } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { useErrorText } from "@/lib/hooks";

const infoSchema = z.object({
  disclosure: z.object({
    identity: z.string(),
    can: z.string(),
    cannot: z.string(),
    retention: z.string(),
  }),
  max_message_length: z.number(),
  max_retention_days: z.number(),
});
const sessionSchema = z.object({ id: z.string(), save_transcript: z.boolean() });
const replySchema = z.object({
  kind: z.enum(["answer", "safety", "unsupported", "unavailable", "limit", "off_policy"]),
  text: z.string(),
  sources: z.array(z.object({ title: z.string(), source: z.string() })),
  actions: z.array(
    z.object({
      type: z.enum(["support", "safety_plan", "helplines", "trusted_contact"]),
      href: z.string(),
    }),
  ),
  level: z.string().nullable(),
});
type Reply = z.infer<typeof replySchema>;
type Turn =
  | { id: number; role: "user"; text: string }
  | { id: number; role: "reply"; reply: Reply; rated?: boolean };

/**
 * The AI chat. The banner says what it is and is not before anything is typed. The
 * conversation lives in this screen's memory only, unless the person turns saving on.
 * Support stays in the shell above the whole time.
 */
export default function ChatPage() {
  const t = useTranslations("chat");
  const common = useTranslations("common");
  const errorText = useErrorText();
  const toast = useToast();
  const inputId = useId();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const counter = useRef(0);
  const nextId = () => (counter.current += 1);

  const info = useQuery({
    queryKey: ["chat-info"],
    queryFn: () => api("/chat/info", { schema: infoSchema }),
    staleTime: 600_000,
  });
  const max = info.data?.max_message_length ?? 1000;
  const days = info.data?.max_retention_days ?? 30;

  const ensureSession = async (): Promise<string> => {
    if (sessionId) return sessionId;
    const session = await api("/chat/sessions", {
      method: "POST",
      body: { save_transcript: saving },
      schema: sessionSchema,
    });
    setSessionId(session.id);
    return session.id;
  };

  const send = useMutation({
    mutationFn: async (message: string) => {
      const id = await ensureSession();
      // With saving off, the earlier turns are sent from this screen's memory.
      const history = turns
        .filter((turn) => turn.role === "user" || turn.reply.kind === "answer")
        .slice(-6)
        .map((turn) =>
          turn.role === "user"
            ? { role: "user", content: turn.text }
            : { role: "assistant", content: turn.reply.text },
        );
      return api(`/chat/sessions/${id}/messages`, {
        method: "POST",
        body: { text: message, history },
        schema: replySchema,
      });
    },
    onMutate: (message) => {
      setTurns((current) => [...current, { id: nextId(), role: "user", text: message }]);
      setText("");
    },
    onSuccess: (reply) =>
      setTurns((current) => [...current, { id: nextId(), role: "reply", reply }]),
  });

  const setSave = useMutation({
    mutationFn: async (on: boolean) => {
      setSaving(on);
      if (sessionId) {
        await api(`/chat/sessions/${sessionId}`, { method: "PATCH", body: { save_transcript: on } });
      }
    },
    onError: (error) => toast(errorText(error)),
  });
  const remove = useMutation({
    mutationFn: async () => {
      if (sessionId) await api(`/chat/sessions/${sessionId}`, { method: "DELETE" });
    },
    onSuccess: () => {
      setSessionId(null);
      setSaving(false);
      setTurns([]);
      toast(t("save.deleted"));
    },
    onError: (error) => toast(errorText(error)),
  });
  const rate = useMutation({
    mutationFn: ({ turn, helpful }: { turn: Turn & { role: "reply" }; helpful: boolean }) =>
      api("/chat/feedback", {
        method: "POST",
        body: { session: sessionId, kind: turn.reply.kind, helpful },
      }),
    onSuccess: (_, { turn }) =>
      setTurns((current) =>
        current.map((item) => (item.id === turn.id ? { ...item, rated: true } : item)),
      ),
  });

  const tooLong = text.length > max;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const message = text.trim();
    if (message && !tooLong && !send.isPending) send.mutate(message);
  };

  return (
    <div>
      <h1 className="h1 mb-4">{t("title")}</h1>

      <section aria-label={t("banner")} className="frame mb-6 p-5" data-chat-banner>
        <p className="h2 mb-3">{info.data?.disclosure.identity ?? t("banner")}</p>
        {info.data ? (
          <dl className="space-y-3 text-dim">
            <div>
              <dt className="font-medium text-moon">{t("can")}</dt>
              <dd>{info.data.disclosure.can}</dd>
            </div>
            <div>
              <dt className="font-medium text-moon">{t("cannot")}</dt>
              <dd>{info.data.disclosure.cannot}</dd>
            </div>
            <div>
              <dt className="font-medium text-moon">{t("retentionTitle")}</dt>
              <dd>{info.data.disclosure.retention}</dd>
            </div>
          </dl>
        ) : info.isError ? (
          <p className="text-warm">{t("error")}</p>
        ) : null}
        <p className="mt-3 text-sm text-dim">{t("limits")}</p>
        <p className="text-sm text-dim">{t("supportHint")}</p>
      </section>

      <section aria-label={t("save.title")} className="mb-6">
        <Toggle
          label={t("save.toggle")}
          hint={saving ? t("save.on", { days }) : t("save.off")}
          checked={saving}
          onChange={(on) => setSave.mutate(on)}
        />
        {turns.length > 0 ? (
          <button type="button" className="btn-text text-sm" onClick={() => remove.mutate()}>
            {saving ? t("save.delete") : t("save.startOver")}
          </button>
        ) : null}
      </section>

      <div role="log" aria-live="polite" aria-label={t("title")} className="mb-6 space-y-4" data-chat-log>
        {turns.length === 0 ? <p className="text-dim">{t("empty")}</p> : null}
        {turns.map((turn) =>
          turn.role === "user" ? (
            <div key={turn.id} className="ml-8 rounded-[14px] bg-raised px-4 py-3" data-turn="user">
              <p className="mb-1 text-sm text-dim">{t("you")}</p>
              <p className="whitespace-pre-wrap">{turn.text}</p>
            </div>
          ) : (
            <div
              key={turn.id}
              className={`mr-8 rounded-[14px] border px-4 py-3 ${
                turn.reply.kind === "safety" ? "border-care" : "border-line-strong"
              }`}
              data-turn={turn.reply.kind}
            >
              <p className="mb-1 text-sm text-dim">{turn.reply.kind === "answer" ? t("ai") : t("fixed")}</p>
              <p className="whitespace-pre-wrap">{turn.reply.text}</p>
              {turn.reply.actions.length > 0 ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {turn.reply.actions.map((item) => (
                    <a
                      key={item.type}
                      href={item.href}
                      className={buttonClass(item.type === "support" ? "care" : "quiet")}
                    >
                      {t(`actions.${item.type}`)}
                    </a>
                  ))}
                </div>
              ) : null}
              {turn.reply.sources.length > 0 ? (
                <div className="mt-3 text-sm text-dim" data-sources>
                  <p>{t("sources")}</p>
                  <ul className="list-disc pl-5">
                    {turn.reply.sources.map((source) => (
                      <li key={source.title}>
                        {source.title} <span className="data">({source.source})</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {turn.reply.kind === "answer" ? (
                <div className="mt-2 flex items-center gap-4">
                  {turn.rated ? (
                    <span className="text-sm text-dim" role="status">
                      {t("feedbackThanks")}
                    </span>
                  ) : (
                    <>
                      <button
                        type="button"
                        className="btn-text text-sm"
                        aria-label={t("helpfulLabel")}
                        onClick={() => rate.mutate({ turn, helpful: true })}
                      >
                        {t("helpful")}
                      </button>
                      <button
                        type="button"
                        className="btn-text text-sm"
                        aria-label={t("notHelpfulLabel")}
                        onClick={() => rate.mutate({ turn, helpful: false })}
                      >
                        {t("notHelpful")}
                      </button>
                    </>
                  )}
                </div>
              ) : null}
            </div>
          ),
        )}
        {send.isPending ? <p className="text-dim">{t("sending")}</p> : null}
      </div>

      {send.isError ? (
        <div className="mb-4">
          <Notice tone="attention" role="alert">
            <p>{errorText(send.error)}</p>
            <a href="/support" className="link inline-flex min-h-11 items-center">
              {t("openSupport")}
            </a>
          </Notice>
        </div>
      ) : null}

      <form onSubmit={submit} noValidate>
        <label htmlFor={inputId} className="mb-1.5 block font-medium">
          {t("input")}
        </label>
        <p id={`${inputId}-hint`} className="mb-1.5 text-sm text-dim">
          {t("inputHint", { max })}
        </p>
        <textarea
          id={inputId}
          aria-describedby={`${inputId}-hint`}
          aria-invalid={tooLong || undefined}
          rows={3}
          className="control mb-3"
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        {tooLong ? (
          <p role="alert" className="mb-3 text-sm text-warm">
            {t("tooLong", { max })}
          </p>
        ) : null}
        <Button type="submit" busy={send.isPending} disabled={!text.trim() || tooLong}>
          {send.isPending ? common("loading") : t("send")}
        </Button>
      </form>
    </div>
  );
}
