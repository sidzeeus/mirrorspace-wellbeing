"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { type FormEvent, useEffect, useId, useRef, useState } from "react";

import { CatFace, type Expression } from "@/components/pet/CatFace";
import { Pet } from "@/components/pet/Pet";
import AnimatedGradientBackground from "@/components/ui/animated-gradient-background";
import { Toggle, useToast } from "@/components/ui/controls";
import { Button, Notice, buttonClass } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { keys, useErrorText } from "@/lib/hooks";
import { type Reflection, page, reflectionSchema, ventEntrySchema } from "@/lib/schemas";

const MAX = 5000;

type Kind = Reflection["reaction"];
/**
 * How Sushi answers each reaction. Only gentle things: curious, a little sad with you,
 * a short huff that settles into calm, slow breathing to follow, a happy hop, a friend
 * who comes to sit beside you. Never alarmed, and never gone.
 */
const FACES: Record<Kind, Expression> = {
  listening: "curious",
  heavy: "sad",
  racing: "calm",
  storm: "upset",
  alone: "sad",
  lighter: "happy",
  steady: "calm",
};

/** Sushi on the Vent screen. After a storm, the huff settles into calm. */
function VentSushi({ kind, typing, label }: { kind: Kind; typing: boolean; label: string }) {
  const [settled, setSettled] = useState(false);
  useEffect(() => {
    if (kind !== "storm") return;
    const timer = window.setTimeout(() => setSettled(true), 3000);
    return () => window.clearTimeout(timer);
  }, [kind]);
  const expression: Expression = typing ? "curious" : kind === "storm" && settled ? "calm" : FACES[kind];
  return (
    <div className="relative p-6">
      <CatFace
        label={label}
        expression={expression}
        breathing={kind === "racing" && !typing}
        hop={kind === "lighter" && !typing}
      />
      {kind === "alone" ? (
        <Pet species="bunny" coat="lilac" mood="alone" className="absolute bottom-2 right-0 w-16" />
      ) : null}
    </div>
  );
}

const NEXT: Record<Kind, readonly { key: string; href: string }[]> = {
  listening: [],
  heavy: [{ key: "plan", href: "/plan" }],
  racing: [{ key: "breathe", href: "/support#calm" }],
  storm: [{ key: "breathe", href: "/support#calm" }],
  alone: [{ key: "message", href: "/support#message" }],
  lighter: [{ key: "checkIn", href: "/check-in" }],
  steady: [
    { key: "support", href: "/support" },
    { key: "plan", href: "/support#plan" },
    { key: "helplines", href: "/support#call" },
  ],
};

/**
 * The light behind the figure, tinted for each reaction. Translucent, so it works on
 * both themes. Never red: even anger gets a warm violet, not an alarm colour.
 */
const GLOWS: Record<Kind, { colors: string[]; speed: number }> = {
  listening: { colors: ["rgb(124 116 242 / 0.32)", "rgb(124 116 242 / 0.1)", "transparent"], speed: 0.02 },
  heavy: { colors: ["rgb(72 82 170 / 0.3)", "rgb(40 46 110 / 0.12)", "transparent"], speed: 0.01 },
  racing: { colors: ["rgb(96 196 200 / 0.3)", "rgb(96 150 220 / 0.1)", "transparent"], speed: 0.03 },
  storm: { colors: ["rgb(176 110 236 / 0.34)", "rgb(140 90 210 / 0.12)", "transparent"], speed: 0.04 },
  alone: { colors: ["rgb(110 160 240 / 0.3)", "rgb(124 116 242 / 0.12)", "transparent"], speed: 0.02 },
  lighter: { colors: ["rgb(127 214 194 / 0.36)", "rgb(185 180 255 / 0.12)", "transparent"], speed: 0.02 },
  steady: { colors: ["rgb(185 180 255 / 0.3)", "rgb(124 116 242 / 0.1)", "transparent"], speed: 0.008 },
};
const GLOW_STOPS = [0, 45, 100];

function KeptEntries() {
  const t = useTranslations("vent.entries");
  const format = useFormatter();
  const toast = useToast();
  const errorText = useErrorText();
  const queryClient = useQueryClient();
  const entries = useQuery({
    queryKey: keys.vent,
    queryFn: () => api("/vent-entries?page_size=50", { schema: page(ventEntrySchema) }),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api(`/vent-entries/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast(t("deleted"));
      void queryClient.invalidateQueries({ queryKey: keys.vent });
    },
    onError: (error) => toast(errorText(error)),
  });

  return (
    <section aria-labelledby="kept-title">
      <h2 id="kept-title" className="h2 mb-4">
        {t("title")}
      </h2>
      {entries.isError ? (
        <Notice tone="attention">{errorText(entries.error)}</Notice>
      ) : entries.data?.results.length ? (
        <ul className="frame divide-y divide-line">
          {entries.data.results.map((entry) => {
            const date = format.dateTime(new Date(entry.created_at), {
              dateStyle: "medium",
              timeStyle: "short",
            });
            return (
              <li key={entry.id} className="p-4" data-vent-entry>
                <details>
                  <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3">
                    <span className="data text-dim">{date}</span>
                    <span className="text-sm">{t("show")}</span>
                  </summary>
                  <p className="mt-3 whitespace-pre-wrap">{entry.body}</p>
                </details>
                <Button
                  variant="quiet"
                  className="mt-3"
                  aria-label={t("deleteNamed", { date })}
                  busy={remove.isPending && remove.variables === entry.id}
                  onClick={() => remove.mutate(entry.id)}
                >
                  {t("delete")}
                </Button>
              </li>
            );
          })}
        </ul>
      ) : entries.isPending ? null : (
        <p className="text-dim">{t("empty")}</p>
      )}
    </section>
  );
}

export function VentPanel() {
  const t = useTranslations("vent");
  const errorText = useErrorText();
  const queryClient = useQueryClient();
  const inputId = useId();
  const resultRef = useRef<HTMLDivElement>(null);
  const [text, setText] = useState("");
  const [keep, setKeep] = useState(false);
  const [typing, setTyping] = useState(false);
  const [result, setResult] = useState<{ reflection: Reflection; kept: boolean } | null>(null);
  const [reactions, setReactions] = useState(0);
  const tooLong = text.length > MAX;

  useEffect(() => {
    if (!typing) return;
    const timer = window.setTimeout(() => setTyping(false), 1200);
    return () => window.clearTimeout(timer);
  }, [typing, text]);

  const letItOut = useMutation({
    mutationFn: async () => {
      const body = text.trim();
      // The reaction first: if the student asked to keep the entry, it is saved only
      // after the reaction worked, so a failure never leaves half of a step done.
      const reflection = await api("/vent/reflect", {
        method: "POST",
        body: { text: body },
        schema: reflectionSchema,
      });
      if (keep) await api("/vent-entries", { method: "POST", body: { body } });
      return { reflection, kept: keep };
    },
    onSuccess: (outcome) => {
      setResult(outcome);
      setReactions((count) => count + 1);
      setText("");
      if (outcome.kept) void queryClient.invalidateQueries({ queryKey: keys.vent });
      // Move focus to the reaction so a screen reader hears it, and nothing is lost.
      window.setTimeout(() => resultRef.current?.focus(), 50);
    },
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!text.trim() || tooLong) return;
    letItOut.mutate();
  };

  const kind: Kind = result?.reflection.reaction ?? "listening";
  const level = result?.reflection.level ?? null;

  return (
    <div className="space-y-12">
      <div>
        <h1 className="h1 mb-3">{t("title")}</h1>
        <p className="mb-1 text-lg">{t("intro")}</p>
        <p className="prose-width text-dim">{t("how")}</p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_16rem] lg:items-start">
        <div className="frame mx-auto w-48 overflow-hidden sm:w-56 lg:order-last lg:sticky lg:top-8 lg:w-full">
          <div className="relative isolate">
            <AnimatedGradientBackground
              key={kind}
              Breathing
              startingGap={70}
              breathingRange={8}
              topOffset={10}
              animationSpeed={GLOWS[kind].speed}
              gradientColors={GLOWS[kind].colors}
              gradientStops={GLOW_STOPS}
              containerClassName="-z-10"
            />
            {/* Keyed by reaction so each new reaction plays from the start. */}
            <VentSushi
              key={`${kind}-${reactions}`}
              kind={kind}
              typing={typing && !result}
              label={`${t("figure")}. ${t(`reactions.${kind}.figure`)}`}
            />
          </div>
          <p className="label border-t border-line px-3 py-2 text-center text-dim" aria-hidden="true">
            {t(`reactions.${kind}.figure`)}
          </p>
        </div>

        <div className="space-y-6">
          <form onSubmit={submit} noValidate className="space-y-4" data-vent-form>
            <div>
              <label htmlFor={inputId} className="mb-1.5 block font-medium">
                {t("label")}
              </label>
              <p id={`${inputId}-hint`} className="mb-1.5 text-sm text-dim">
                {t("hint", { max: MAX })}
              </p>
              <textarea
                id={inputId}
                aria-describedby={`${inputId}-hint`}
                aria-invalid={tooLong || undefined}
                rows={9}
                className="control min-h-56 resize-y leading-relaxed"
                value={text}
                onChange={(event) => {
                  setText(event.target.value);
                  setTyping(true);
                }}
              />
              {tooLong ? (
                <p role="alert" className="mt-2 text-sm text-warm">
                  {t("tooLong", { max: MAX })}
                </p>
              ) : null}
            </div>
            <Toggle label={t("keep")} hint={t("keepHint")} checked={keep} onChange={setKeep} />
            <Button type="submit" busy={letItOut.isPending} disabled={!text.trim() || tooLong}>
              {letItOut.isPending ? t("submitting") : t("submit")}
            </Button>
            {letItOut.isError ? (
              <Notice tone="attention" role="alert">
                {t("unavailable")} {errorText(letItOut.error)}
              </Notice>
            ) : null}
          </form>

          {result ? (
            <div
              ref={resultRef}
              tabIndex={-1}
              role="status"
              className="space-y-4 border-t border-line pt-6 outline-none"
              data-vent-reaction={kind}
            >
              <p className="label text-dim">{result.kept ? t("kept") : t("released")}</p>
              {level === "crisis" ? (
                <Notice tone="attention">
                  <span className="block">{t("reactions.steady.line")}</span>
                  <span className="mt-2 block">{t("emergency")}</span>
                </Notice>
              ) : (
                <p className="text-lg">{t(`reactions.${kind}.line`)}</p>
              )}
              {level === "distress" ? <p className="text-dim">{t("distress")}</p> : null}
              <div className="flex flex-wrap gap-3">
                {(level === "distress" ? [...NEXT[kind], { key: "support", href: "/support" }] : NEXT[kind]).map(
                  (next) => (
                    <Link
                      key={next.key}
                      href={next.href}
                      className={buttonClass(level === "crisis" && next.key === "support" ? "care" : "quiet")}
                    >
                      {t(`next.${next.key}`)}
                    </Link>
                  ),
                )}
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <KeptEntries />
    </div>
  );
}
