"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Toggle, useToast } from "@/components/ui/controls";
import { Notice, buttonClass } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { CATEGORIES } from "@/lib/constants";
import { useErrorText, useExercises } from "@/lib/hooks";
import type { Exercise } from "@/lib/schemas";

type Filter = "all" | (typeof CATEGORIES)[number];

export default function ExercisesPage() {
  const t = useTranslations("exercises");
  const common = useTranslations("common");
  const errorText = useErrorText();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<Filter>("all");
  const [showHidden, setShowHidden] = useState(false);
  const exercises = useExercises(showHidden);

  const record = useMutation({
    mutationFn: ({ exercise, kind }: { exercise: Exercise; kind: string }) =>
      api("/exercise-events", { method: "POST", body: { exercise: exercise.id, kind } }),
    onSuccess: (_, { exercise, kind }) => {
      void queryClient.invalidateQueries({ queryKey: ["exercises"] });
      if (kind === "not_helpful") toast(t("notHelpfulDone"));
      if (kind === "hidden") {
        toast(t("hidden"), {
          label: t("undo"),
          run: () => record.mutate({ exercise, kind: "unhidden" }),
        });
      }
    },
    onError: (error) => toast(errorText(error)),
  });

  const all = exercises.data?.results ?? [];
  const available = CATEGORIES.filter((category) => all.some((item) => item.category === category));
  const shown = all.filter((item) => filter === "all" || item.category === filter);

  return (
    <div>
      <h1 className="h1 mb-3">{t("title")}</h1>
      <p className="prose-width mb-8 text-dim">{t("intro")}</p>

      {exercises.isError ? (
        <Notice tone="attention" role="alert">
          <p>{t("error")}</p>
          <p className="text-dim">{errorText(exercises.error)}</p>
          <button type="button" className="btn-text" onClick={() => void exercises.refetch()}>
            {common("tryAgain")}
          </button>
        </Notice>
      ) : exercises.isPending ? (
        <p role="status" className="text-dim">
          {common("loading")}
        </p>
      ) : all.length === 0 && !showHidden ? (
        <p className="prose-width text-dim">{t("empty")}</p>
      ) : (
        <>
          <fieldset className="mb-6">
            <legend className="mb-2 font-medium">{t("filter")}</legend>
            <div className="flex flex-wrap gap-2">
              {(["all", ...available] as const).map((option) => (
                <button
                  key={option}
                  type="button"
                  aria-pressed={filter === option}
                  onClick={() => setFilter(option)}
                  className={`min-h-11 rounded-[14px] border px-4 ${
                    filter === option
                      ? "border-lumen-hi bg-lumen-hi text-on-lumen"
                      : "border-line-strong bg-surface hover:bg-raised"
                  }`}
                >
                  {option === "all" ? t("all") : t(`categories.${option}`)}
                </button>
              ))}
            </div>
          </fieldset>

          {shown.length === 0 ? (
            <p className="text-dim">{t("emptyFilter")}</p>
          ) : (
            <ul className="frame divide-y divide-line">
              {shown.map((exercise) => (
                <li key={exercise.id} className="p-5" data-exercise={exercise.slug}>
                  <div className="mb-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                    <h2 className="h2">{exercise.title}</h2>
                    {exercise.hidden ? <span className="data text-dim">{t("hiddenTag")}</span> : null}
                  </div>
                  <p className="mb-1 text-dim">{exercise.summary}</p>
                  <p className="data mb-4 text-dim">
                    {t(`categories.${exercise.category}`)} ·{" "}
                    {t("minutes", { minutes: exercise.duration_minutes })}
                  </p>
                  <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
                    <Link
                      href={`/exercises/${exercise.id}`}
                      aria-label={t("openLabel", { title: exercise.title })}
                      className={buttonClass("primary")}
                    >
                      {t("open")}
                    </Link>
                    <button
                      type="button"
                      className="btn-text"
                      aria-label={t("notHelpfulLabel", { title: exercise.title })}
                      onClick={() => record.mutate({ exercise, kind: "not_helpful" })}
                    >
                      {t("notHelpful")}
                    </button>
                    {exercise.hidden ? (
                      <button
                        type="button"
                        className="btn-text"
                        aria-label={t("showLabel", { title: exercise.title })}
                        onClick={() => record.mutate({ exercise, kind: "unhidden" })}
                      >
                        {t("undo")}
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="btn-text"
                        aria-label={t("hideLabel", { title: exercise.title })}
                        onClick={() => record.mutate({ exercise, kind: "hidden" })}
                      >
                        {t("hide")}
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      <div className="mt-6">
        <Toggle label={t("showHidden")} checked={showHidden} onChange={setShowHidden} />
      </div>
    </div>
  );
}
