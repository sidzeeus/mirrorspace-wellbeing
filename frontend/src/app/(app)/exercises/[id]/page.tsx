"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";

import { SupportLink } from "@/components/AppShell";
import { BreathingPlayer } from "@/components/BreathingPlayer";
import { Button, Notice, UnreviewedBadge, buttonClass } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { useOfflineExercises } from "@/lib/offline";

type Stage = "doing" | "done" | "thanked";
const noop = () => () => undefined;

/**
 * The full-screen, distraction-free player. It covers the navigation, but Support and
 * "End" stay in the top bar at all times.
 */
export default function ExercisePlayerPage() {
  const t = useTranslations("exercises.player");
  const common = useTranslations("common");
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  // Read from the already-loaded list, so an exercise opened once works offline.
  const exercises = useOfflineExercises();
  const exercise = exercises.data?.data.find((item) => item.id === id);
  const mounted = useSyncExternalStore(
    noop,
    () => true,
    () => false,
  );
  const [step, setStep] = useState(0);
  const [stage, setStage] = useState<Stage>("doing");
  const [failed, setFailed] = useState(false);

  const record = useMutation({
    mutationFn: (kind: string) =>
      api("/exercise-events", { method: "POST", body: { exercise: id, kind } }),
    onError: () => setFailed(true),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["exercises"] }),
  });
  const finish = () => {
    setStage("done");
    record.mutate("completed");
  };
  const feedback = (kind: "helpful" | "not_helpful") => {
    record.mutate(kind);
    setStage("thanked");
  };

  const breathing =
    exercise?.category === "breathing" && exercise.pattern.inhale && exercise.pattern.exhale
      ? { inhale: exercise.pattern.inhale, exhale: exercise.pattern.exhale }
      : null;

  // Rendered into <body>, outside the page column, so it truly covers the navigation.
  if (!mounted) return null;
  return createPortal(
    <div className="fixed inset-0 z-40 flex flex-col overflow-y-auto bg-ink" data-player>
      <header className="flex h-16 shrink-0 items-center justify-between gap-3 border-b border-line px-5">
        <Link href="/exercises" aria-label={t("endLabel")} className={buttonClass("quiet")}>
          {t("end")}
        </Link>
        <SupportLink />
      </header>

      <div className="mx-auto flex w-full max-w-xl grow flex-col justify-center px-5 py-8">
        {!exercise ? (
          <div>
            <p role="status" className="mb-4 text-dim">
              {exercises.isPending ? common("loading") : t("notFound")}
            </p>
            <Link href="/exercises" className={buttonClass("quiet")}>
              {t("backToList")}
            </Link>
          </div>
        ) : stage !== "doing" ? (
          <div>
            <h1 className="h1 mb-3">{t("doneTitle")}</h1>
            {stage === "thanked" ? (
              <Notice tone="saved" role="status">
                {t("thanks")}
              </Notice>
            ) : (
              <>
                <p className="mb-6 text-dim">{t("doneBody")}</p>
                <div className="grid grid-cols-3 gap-3">
                  <Button variant="quiet" onClick={() => feedback("helpful")}>
                    {t("helpful")}
                  </Button>
                  <Button variant="quiet" onClick={() => feedback("not_helpful")}>
                    {t("notHelpful")}
                  </Button>
                  <Link href="/exercises" className={buttonClass("quiet")}>
                    {t("skipFeedback")}
                  </Link>
                </div>
              </>
            )}
            {failed ? (
              <div className="mt-4">
                <Notice tone="attention" role="alert">
                  {t("feedbackFailed")}
                </Notice>
              </div>
            ) : null}
            {stage === "thanked" ? (
              <p className="mt-6">
                <Link href="/exercises" className={buttonClass("quiet")}>
                  {t("backToList")}
                </Link>
              </p>
            ) : null}
          </div>
        ) : (
          <div>
            <h1 className="h1 mb-2 flex flex-wrap items-center gap-3">{exercise.title}</h1>
            {exercise.reviewed ? null : (
              <p className="mb-2">
                <UnreviewedBadge>{t("placeholder")}</UnreviewedBadge>
              </p>
            )}
            <p className="mb-8 text-dim">{exercise.summary}</p>

            {breathing ? (
              <BreathingPlayer
                inhale={breathing.inhale}
                exhale={breathing.exhale}
                minutes={exercise.duration_minutes}
                onFinish={finish}
              />
            ) : (
              <>
                <p className="data mb-3 text-dim" aria-live="polite">
                  {t("step", { current: step + 1, total: exercise.steps.length })}
                </p>
                <p className="mb-10 min-h-24 text-2xl font-light leading-snug">{exercise.steps[step]}</p>
              </>
            )}

            <div className="mt-8 grid grid-cols-2 gap-3">
              {breathing ? (
                <Button variant="quiet" className="col-span-2" onClick={finish}>
                  {t("finish")}
                </Button>
              ) : (
                <>
                  <Button variant="quiet" disabled={step === 0} onClick={() => setStep(step - 1)}>
                    {t("previous")}
                  </Button>
                  {step < exercise.steps.length - 1 ? (
                    <Button onClick={() => setStep(step + 1)}>{t("next")}</Button>
                  ) : (
                    <Button onClick={finish}>{t("finish")}</Button>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}
