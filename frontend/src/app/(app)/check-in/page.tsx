"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Pet, type PetMood } from "@/components/pet/Pet";
import { ScaleControl, Slider } from "@/components/ui/controls";
import { Button, Notice, Panel, buttonClass } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { SCALE } from "@/lib/constants";
import { localDate, useErrorText, useExercises, useMe } from "@/lib/hooks";
import { type CheckIn, checkInSchema, page } from "@/lib/schemas";

type Answers = {
  mood: number | null;
  sleep_hours: number | null;
  sleep_quality: number | null;
  energy: number | null;
  stress: number | null;
};
const EMPTY: Answers = { mood: null, sleep_hours: null, sleep_quality: null, energy: null, stress: null };

function fromCheckIn(row: CheckIn): Answers {
  return {
    mood: row.mood,
    sleep_hours: row.sleep_hours === null ? null : Number(row.sleep_hours),
    sleep_quality: row.sleep_quality,
    energy: row.energy,
    stress: row.stress,
  };
}

/**
 * The daily check-in: four optional answers, one screen, done in under twenty
 * seconds. A pet shows the mood answer as it changes, with the same information
 * in words for anyone who cannot see it. Skipping is always possible and saves nothing.
 */
/** How the pet sits for each mood answer, 1 (low) to 5 (good); 0 is unanswered. */
const MOOD_POSES: readonly PetMood[] = ["idle", "heavy", "steady", "idle", "listening", "lighter"];

/** The check-in stays taps only; anything longer has its own private place. */
function VentPrompt() {
  const t = useTranslations("checkin");
  return (
    <p className="mt-6 text-dim">
      {t("ventPrompt")}{" "}
      <Link href="/vent" className="link inline-flex min-h-11 items-center">
        {t("ventLink")}
      </Link>
    </p>
  );
}

export default function CheckInPage() {
  const common = useTranslations("common");
  const me = useMe();
  const today = localDate(me.data?.timezone ?? "UTC");
  const existing = useQuery({
    queryKey: ["check-in-today", today],
    queryFn: async () =>
      (await api(`/check-ins?from=${today}&to=${today}`, { schema: page(checkInSchema) }))
        .results[0] ?? null,
    // Always read fresh when the screen opens, and never refetch while it is open:
    // a refetch after saving would rebuild the form and hide the confirmation.
    staleTime: 0,
    gcTime: 0,
    refetchOnReconnect: false,
  });
  if (existing.isPending) {
    return (
      <p role="status" className="text-dim">
        {common("loading")}
      </p>
    );
  }
  // Keyed so the form starts from what was saved earlier today, if anything.
  return <CheckInForm key={existing.data?.id ?? "new"} saved={existing.data ?? null} />;
}

function CheckInForm({ saved }: { saved: CheckIn | null }) {
  const t = useTranslations("checkin");
  const common = useTranslations("common");
  const errorText = useErrorText();
  const queryClient = useQueryClient();
  const [answers, setAnswers] = useState<Answers>(saved ? fromCheckIn(saved) : EMPTY);
  const [empty, setEmpty] = useState(false);

  const exercises = useExercises();
  const save = useMutation({
    mutationFn: () =>
      api("/check-ins", {
        method: "POST",
        body: { ...answers, sleep_hours: answers.sleep_hours?.toFixed(1) ?? null },
        schema: checkInSchema,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["check-ins"] });
      void queryClient.invalidateQueries({ queryKey: ["patterns"] });
    },
  });

  const set = (change: Partial<Answers>) => {
    setAnswers((current) => ({ ...current, ...change }));
    setEmpty(false);
  };
  const levels = SCALE.map((value) => ({ value, name: t(`level.${value}`) }));
  const sleepLevels = SCALE.map((value) => ({ value, name: t(`sleepLevel.${value}`) }));
  const mood = answers.mood;

  if (save.isSuccess) {
    const suggestion =
      exercises.data?.results.find((exercise) => exercise.category === "breathing") ??
      exercises.data?.results[0];
    return (
      <div className="mx-auto max-w-xl">
        <h1 className="h1 mb-6">{t("title")}</h1>
        <Notice tone="saved" role="status">
          {t("saved")}
        </Notice>
        <VentPrompt />
        {suggestion ? (
          <section aria-labelledby="after-title" className="mt-8">
            <h2 id="after-title" className="h2 mb-2">
              {t("after.title")}
            </h2>
            <p className="mb-4 text-dim">{t("after.body")}</p>
            <div className="frame mb-5 p-5">
              <p className="mb-1 flex flex-wrap items-center gap-2 font-medium">
                {suggestion.title}
              </p>
              <p className="text-dim">{suggestion.summary}</p>
            </div>
            {/* Two equal buttons: declining is exactly as easy as accepting. */}
            <div className="grid grid-cols-2 gap-3">
              <Link href={`/exercises/${suggestion.id}`} className={buttonClass("quiet")}>
                {t("after.open")}
              </Link>
              <Link href="/home" className={buttonClass("quiet")}>
                {t("after.notNow")}
              </Link>
            </div>
          </section>
        ) : (
          <>
            <p className="my-6 text-dim">{t("after.none")}</p>
            <Link href="/home" className={buttonClass("quiet")}>
              {common("back")}
            </Link>
          </>
        )}
      </div>
    );
  }

  return (
    <form
      noValidate
      className="mx-auto max-w-xl"
      onSubmit={(event) => {
        event.preventDefault();
        if (Object.values(answers).every((value) => value === null)) setEmpty(true);
        else save.mutate();
      }}
    >
      <h1 className="h1 mb-3">{t("title")}</h1>
      <p className="mb-6 text-dim">{saved ? t("editing") : t("intro")}</p>

      <Panel className="mx-auto mb-6 w-44 p-4 sm:w-52">
        <Pet
          label={t("lumen", { state: t(`lumenStates.${mood ?? "unset"}`) })}
          species="cat"
          mood={MOOD_POSES[mood ?? 0] ?? "idle"}
        />
      </Panel>
      <p className="sr-only" aria-live="polite">
        {mood === null ? "" : t(`lumenStates.${mood}`)}
      </p>

      <div className="space-y-8">
        <div>
          <Slider
            label={t("mood")}
            value={mood ?? 3}
            onChange={(value) => set({ mood: value })}
            valueText={mood === null ? t("moodUnset") : `${mood}: ${t(`level.${mood}`)}`}
            minLabel={t("level.1")}
            maxLabel={t("level.5")}
          />
          {mood !== null ? (
            <button type="button" className="btn-text text-sm" onClick={() => set({ mood: null })}>
              {t("moodClear")}
            </button>
          ) : null}
        </div>

        <div role="group" aria-labelledby="sleep-hours-label">
          <div className="mb-2 flex items-baseline justify-between gap-4">
            <span id="sleep-hours-label" className="font-medium">
              {t("sleepHours")}
            </span>
            <span className="data text-dim" aria-live="polite">
              {answers.sleep_hours === null
                ? t("sleepUnset")
                : t("sleepHoursValue", { hours: answers.sleep_hours })}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="quiet"
              className="h-12 grow text-xl"
              aria-label={t("less")}
              onClick={() => set({ sleep_hours: Math.max(0, (answers.sleep_hours ?? 7.5) - 0.5) })}
            >
              −
            </Button>
            <Button
              variant="quiet"
              className="h-12 grow text-xl"
              aria-label={t("more")}
              onClick={() => set({ sleep_hours: Math.min(24, (answers.sleep_hours ?? 6.5) + 0.5) })}
            >
              +
            </Button>
          </div>
          {answers.sleep_hours !== null ? (
            <button type="button" className="btn-text text-sm" onClick={() => set({ sleep_hours: null })}>
              {t("clear")}
            </button>
          ) : null}
        </div>

        <ScaleControl
          label={t("sleepQuality")}
          value={answers.sleep_quality}
          onChange={(value) => set({ sleep_quality: value })}
          options={sleepLevels}
          clearLabel={t("clear")}
        />
        <ScaleControl
          label={t("energy")}
          value={answers.energy}
          onChange={(value) => set({ energy: value })}
          options={levels}
          clearLabel={t("clear")}
        />
        <ScaleControl
          label={t("stress")}
          value={answers.stress}
          onChange={(value) => set({ stress: value })}
          options={levels}
          clearLabel={t("clear")}
        />
      </div>

      <div className="mt-8 space-y-3">
        {empty ? (
          <Notice tone="attention" role="alert">
            {t("nothing")}
          </Notice>
        ) : null}
        {save.isError ? (
          <Notice tone="attention" role="alert">
            {errorText(save.error)}
          </Notice>
        ) : null}
        <div className="grid grid-cols-2 gap-3">
          <Button type="submit" busy={save.isPending}>
            {t("save")}
          </Button>
          <Link href="/home" className={buttonClass("quiet")}>
            {t("skip")}
          </Link>
        </div>
        <VentPrompt />
      </div>
    </form>
  );
}
