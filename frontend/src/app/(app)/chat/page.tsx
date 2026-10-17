"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import {
  type FormEvent,
  type KeyboardEvent,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { z } from "zod";

import { CatFace } from "@/components/pet/CatFace";
import { Toggle, useToast } from "@/components/ui/controls";
import { Notice, buttonClass } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { useErrorText } from "@/lib/hooks";
import { useReducedMotion } from "@/lib/prefs";
import { speechLang, useSpeechRecognition, useSpeechSynthesis } from "@/lib/voice";

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
  plan: z
    .object({ matched: z.array(z.string()), coping_steps: z.array(z.string()), href: z.string() })
    .nullable()
    .optional(),
});
type Reply = z.infer<typeof replySchema>;
const contextSchema = z.object({ enabled: z.boolean(), preview: z.string() });
type Turn =
  | { id: number; role: "user"; text: string }
  | { id: number; role: "reply"; reply: Reply; rated?: boolean };

const SUGGESTIONS = ["stressed", "sleep", "lonely", "talk"] as const;

function Icon({ path, className = "" }: { path: string; className?: string }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <path d={path} />
    </svg>
  );
}

const ICONS = {
  send: "M5 12h13M13 6l6 6-6 6",
  mic: "M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3ZM5 11a7 7 0 0 0 14 0M12 18v3",
  stop: "M7 7h10v10H7z",
  speaker: "M4 9v6h4l5 4V5L8 9H4ZM16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12",
  speakerOff: "M4 9v6h4l5 4V5L8 9H4ZM17 9l5 6M22 9l-5 6",
  settings:
    "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1",
  up: "M7 10v10H4V10h3Zm0 0 4-7a2 2 0 0 1 2 2v4h5.5a2 2 0 0 1 2 2.3l-1.2 6.5a2 2 0 0 1-2 1.7H7",
  down: "M17 14V4h3v10h-3Zm0 0-4 7a2 2 0 0 1-2-2v-4H5.5a2 2 0 0 1-2-2.3l1.2-6.5a2 2 0 0 1 2-1.7H17",
} as const;

/**
 * The AI chat, laid out like any messaging app: Sushi's messages on the left, yours on
 * the right, one box at the bottom. Enter sends; Shift+Enter adds a line.
 *
 * What stays, whatever the layout: a line saying Sushi is an AI and nobody monitors the
 * chat, the full disclosure one tap away, saving off unless turned on, and Support in
 * the shell above. The conversation lives in this screen's memory unless saving is on.
 *
 * Voice is optional: the mic listens once and sends what was said; a reply to a spoken
 * message is read aloud, as is every reply when "read aloud" is on.
 */
export default function ChatPage() {
  const t = useTranslations("chat");
  const errorText = useErrorText();
  const toast = useToast();
  const inputId = useId();
  const aboutId = useId();
  const settingsId = useId();
  const still = useReducedMotion();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const counter = useRef(0);
  const nextId = () => (counter.current += 1);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const lang = speechLang(useLocale());
  const listen = useSpeechRecognition(lang);
  const voice = useSpeechSynthesis(lang);
  const [readAloud, setReadAloud] = useState(false);
  // The last message was spoken, so its reply is spoken back.
  const spokenTurn = useRef(false);

  const queryClient = useQueryClient();
  // Whether Sushi may see a summary of this person's own records (off unless turned on).
  const sharing = useQuery({
    queryKey: ["chat-context"],
    queryFn: () => api("/chat/context", { schema: contextSchema }),
  });
  const setSharing = useMutation({
    mutationFn: (enabled: boolean) =>
      api("/chat/context", { method: "PUT", body: { enabled }, schema: contextSchema }),
    onSuccess: (data) => queryClient.setQueryData(["chat-context"], data),
    onError: (error) => toast(errorText(error)),
  });

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
        .slice(-20)
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
    onSuccess: (reply) => {
      setTurns((current) => [...current, { id: nextId(), role: "reply", reply }]);
      if (spokenTurn.current || readAloud) voice.speak(reply.text);
      spokenTurn.current = false;
    },
    onError: () => {
      spokenTurn.current = false;
    },
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
      voice.stop();
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

  // Keep the newest message in view.
  useEffect(() => {
    if (turns.length || send.isPending) {
      endRef.current?.scrollIntoView({ behavior: still ? "auto" : "smooth", block: "end" });
    }
  }, [turns.length, send.isPending, still]);

  // The box grows with what is typed, up to about six lines.
  useLayoutEffect(() => {
    const box = inputRef.current;
    if (!box) return;
    box.style.height = "auto";
    box.style.height = `${Math.min(box.scrollHeight, 168)}px`;
  }, [text]);

  const tooLong = text.length > max;
  const sendText = (message: string, spoken = false) => {
    const clean = message.trim();
    if (!clean || clean.length > max || send.isPending) return;
    spokenTurn.current = spoken;
    send.mutate(clean);
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    sendText(text);
  };
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter sends; Shift+Enter is a new line; never interrupt typing with an input method.
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      sendText(text);
    }
  };

  const talk = () => {
    if (listen.listening) {
      listen.stop();
      return;
    }
    voice.stop();
    listen.start({
      onInterim: (heard) => setText(heard),
      onFinal: (heard) => sendText(heard, true),
      onError: (code) => toast(t(`voice.errors.${code}`)),
    });
  };

  return (
    <div className="flex min-h-[calc(100dvh-14rem)] flex-col lg:min-h-[calc(100dvh-7rem)]">
      {/* Who you are talking to, and the settings, in one quiet bar. */}
      <header className="mb-3 flex items-center gap-3">
        <CatFace
          label={voice.speaking ? t("faceTalking") : t("face")}
          talking={voice.speaking}
          thinking={send.isPending}
          className="w-16 shrink-0"
        />
        <div className="grow">
          <h1 className="text-lg font-medium leading-tight">{t("title")}</h1>
          <p className="text-sm text-dim">{t("subtitle")}</p>
        </div>
        {voice.supported ? (
          <button
            type="button"
            className="btn btn-quiet min-w-11! px-0!"
            aria-pressed={readAloud}
            aria-label={t("voice.readAloud")}
            title={t("voice.readAloud")}
            onClick={() => {
              setReadAloud(!readAloud);
              if (readAloud) voice.stop();
            }}
          >
            <Icon path={readAloud ? ICONS.speaker : ICONS.speakerOff} />
          </button>
        ) : null}
        <button
          type="button"
          className="btn btn-quiet min-w-11! px-0!"
          aria-expanded={settingsOpen}
          aria-controls={settingsId}
          aria-label={t("settings")}
          title={t("settings")}
          onClick={() => setSettingsOpen(!settingsOpen)}
        >
          <Icon path={ICONS.settings} />
        </button>
      </header>

      {settingsOpen ? (
        <section id={settingsId} aria-label={t("settings")} className="frame mb-4 space-y-3 p-4" data-voice-settings>
          <Toggle
            label={t("save.toggle")}
            hint={saving ? t("save.on", { days }) : t("save.off")}
            checked={saving}
            onChange={(on) => setSave.mutate(on)}
          />
          <div data-chat-context>
            <Toggle
              label={t("context.toggle")}
              hint={sharing.data?.enabled ? t("context.on") : t("context.off")}
              checked={sharing.data?.enabled ?? false}
              onChange={(on) => setSharing.mutate(on)}
            />
            {sharing.data?.enabled ? (
              <details className="mt-1 text-sm">
                <summary className="link inline-flex min-h-11 cursor-pointer items-center">
                  {t("context.preview")}
                </summary>
                <pre className="whitespace-pre-wrap rounded-2xl border border-line p-3 font-sans text-dim">
                  {sharing.data.preview || t("context.empty")}
                </pre>
              </details>
            ) : null}
          </div>
          {voice.supported ? (
            <Toggle
              label={t("voice.readAloud")}
              hint={t("voice.readAloudHint")}
              checked={readAloud}
              onChange={(on) => {
                setReadAloud(on);
                if (!on) voice.stop();
              }}
            />
          ) : null}
          <p className="text-sm text-dim">
            {listen.supported ? t("voice.privacy") : t("voice.unsupported")}
          </p>
          {turns.length > 0 ? (
            <button type="button" className="btn-text text-sm" onClick={() => remove.mutate()}>
              {saving ? t("save.delete") : t("save.startOver")}
            </button>
          ) : null}
        </section>
      ) : null}

      {/* The AI disclosure: one line always in view, the whole of it one tap away. */}
      <div className="mb-4 text-sm text-dim" data-chat-banner>
        <p>
          {t("aiLine")}{" "}
          <button
            type="button"
            className="link inline-flex min-h-11 items-center"
            aria-expanded={aboutOpen}
            aria-controls={aboutId}
            onClick={() => setAboutOpen(!aboutOpen)}
          >
            {t("about")}
          </button>
        </p>
        {aboutOpen ? (
          <div id={aboutId} className="frame mt-2 p-4">
            <p className="mb-3 font-medium text-moon">{info.data?.disclosure.identity ?? t("banner")}</p>
            {info.data ? (
              <dl className="space-y-3">
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
            <p className="mt-3">{t("limits")}</p>
            <p>{t("supportHint")}</p>
          </div>
        ) : null}
      </div>

      <div role="log" aria-live="polite" aria-label={t("title")} className="grow space-y-4 pb-4" data-chat-log>
        {turns.length === 0 && !send.isPending ? (
          <div className="flex flex-col items-center py-8 text-center">
            <CatFace talking={voice.speaking} className="mb-4 w-32" />
            <p className="h2 mb-1">{t("greeting")}</p>
            <p className="mb-6 text-dim">{t("empty")}</p>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((key) => (
                <button
                  key={key}
                  type="button"
                  className="pill min-h-11 hover:border-moon"
                  onClick={() => sendText(t(`suggestions.${key}`))}
                >
                  {t(`suggestions.${key}`)}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {turns.map((turn) =>
          turn.role === "user" ? (
            <div key={turn.id} className="flex justify-end" data-turn="user">
              <div className="max-w-[85%] rounded-3xl rounded-br-lg bg-accent-hi px-4 py-2.5 text-on-accent">
                <span className="sr-only">{t("you")}: </span>
                <p className="whitespace-pre-wrap">{turn.text}</p>
              </div>
            </div>
          ) : (
            <div key={turn.id} className="flex items-start gap-2" data-turn={turn.reply.kind}>
              <CatFace className="mt-0.5 w-8 shrink-0" />
              <div className="max-w-[85%]">
                <div
                  className={`frame rounded-3xl rounded-tl-lg px-4 py-2.5 ${
                    turn.reply.kind === "safety" ? "border-care!" : ""
                  }`}
                >
                  {turn.reply.kind === "answer" ? (
                    <span className="sr-only">{t("ai")}: </span>
                  ) : (
                    <p className="mb-1 text-xs text-dim">{t("fixed")}</p>
                  )}
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
                  {turn.reply.plan ? (
                    <div className="mt-3 rounded-2xl border border-care/60 p-3" data-plan-card>
                      <p className="mb-2 text-sm font-medium">
                        {t("context.planTitle", { trigger: turn.reply.plan.matched.join(", ") })}
                      </p>
                      {turn.reply.plan.coping_steps.length > 0 ? (
                        <ul className="mb-2 list-disc space-y-1 pl-5 text-sm">
                          {turn.reply.plan.coping_steps.map((step) => (
                            <li key={step}>{step}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="mb-2 text-sm text-dim">{t("context.planEmpty")}</p>
                      )}
                      <a href={turn.reply.plan.href} className="link inline-flex min-h-11 items-center text-sm">
                        {t("context.openPlan")}
                      </a>
                    </div>
                  ) : null}
                  {turn.reply.sources.length > 0 ? (
                    <p className="mt-2 text-xs text-dim" data-sources>
                      {t("sources")}: {turn.reply.sources.map((source) => source.title).join(", ")}
                    </p>
                  ) : null}
                </div>
                {turn.reply.kind === "answer" ? (
                  <div className="mt-1 flex items-center gap-1 pl-2 text-dim">
                    {turn.rated ? (
                      <span className="text-xs" role="status">
                        {t("feedbackThanks")}
                      </span>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="inline-flex size-11 items-center justify-center rounded-full hover:bg-raised hover:text-moon"
                          aria-label={t("helpfulLabel")}
                          onClick={() => rate.mutate({ turn, helpful: true })}
                        >
                          <Icon path={ICONS.up} className="size-4" />
                        </button>
                        <button
                          type="button"
                          className="inline-flex size-11 items-center justify-center rounded-full hover:bg-raised hover:text-moon"
                          aria-label={t("notHelpfulLabel")}
                          onClick={() => rate.mutate({ turn, helpful: false })}
                        >
                          <Icon path={ICONS.down} className="size-4" />
                        </button>
                      </>
                    )}
                  </div>
                ) : null}
              </div>
            </div>
          ),
        )}

        {send.isPending ? (
          <div className="flex items-start gap-2" role="status">
            <CatFace thinking className="mt-0.5 w-8 shrink-0" />
            <div className="frame flex gap-1.5 rounded-3xl rounded-tl-lg px-4 py-4" aria-hidden="true">
              {[0, 1, 2].map((dot) => (
                <span
                  key={dot}
                  className="typing-dot size-2 rounded-full bg-dim"
                  style={{ animationDelay: `${dot * 160}ms` }}
                />
              ))}
            </div>
            <span className="sr-only">{t("sending")}</span>
          </div>
        ) : null}

        {send.isError ? (
          <Notice tone="attention" role="alert">
            <p>{errorText(send.error)}</p>
            <a href="/support" className="link inline-flex min-h-11 items-center">
              {t("openSupport")}
            </a>
          </Notice>
        ) : null}
        {/* Scrolled to with room to spare, so the newest message clears the message box. */}
        <div ref={endRef} className="scroll-mb-56 lg:scroll-mb-32" />
      </div>

      {/* One box, pinned to the bottom, like any chat app. */}
      <form
        onSubmit={submit}
        noValidate
        className="sticky bottom-[8.5rem] z-20 lg:bottom-4"
      >
        <div className="glass flex items-end gap-1 rounded-3xl p-1.5 pl-4 focus-within:ring-2 focus-within:ring-accent-hi">
          <label htmlFor={inputId} className="sr-only">
            {t("input")}
          </label>
          <textarea
            id={inputId}
            ref={inputRef}
            rows={1}
            aria-describedby={`${inputId}-hint`}
            aria-invalid={tooLong || undefined}
            placeholder={listen.listening ? t("voice.listening") : t("placeholder")}
            className="max-h-42 min-h-11 grow resize-none bg-transparent py-2.5 text-moon outline-none placeholder:text-dim focus-visible:outline-none"
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={onKeyDown}
          />
          {listen.supported ? (
            <button
              type="button"
              className={`inline-flex size-11 shrink-0 items-center justify-center rounded-full ${
                listen.listening ? "bg-care text-on-care" : "text-dim hover:bg-raised hover:text-moon"
              }`}
              aria-pressed={listen.listening}
              aria-label={listen.listening ? t("voice.stopListening") : t("voice.talk")}
              title={listen.listening ? t("voice.stopListening") : t("voice.talk")}
              disabled={send.isPending}
              onClick={talk}
              data-voice-talk
            >
              <Icon path={listen.listening ? ICONS.stop : ICONS.mic} />
            </button>
          ) : null}
          <button
            type="submit"
            className="inline-flex size-11 shrink-0 items-center justify-center rounded-full bg-moon text-ink disabled:opacity-40"
            aria-label={t("send")}
            title={t("send")}
            disabled={!text.trim() || tooLong || send.isPending}
          >
            <Icon path={ICONS.send} />
          </button>
        </div>
        <p id={`${inputId}-hint`} className={`mt-1.5 px-4 text-xs ${tooLong ? "text-warm" : "text-dim"}`}>
          {tooLong ? t("tooLong", { max }) : t("inputHint")}
        </p>
        {voice.speaking ? (
          <button type="button" className="btn-text text-sm" onClick={voice.stop} data-voice-stop>
            {t("voice.stopSpeaking")}
          </button>
        ) : null}
      </form>
    </div>
  );
}
