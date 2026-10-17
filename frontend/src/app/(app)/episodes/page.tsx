"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { type FormEvent, useId, useState } from "react";

import { ScaleControl, Tabs, Toggle, useToast } from "@/components/ui/controls";
import { Button, Field, Notice } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { SCALE } from "@/lib/constants";
import { keys, useErrorText, useExercises } from "@/lib/hooks";
import { type Exercise, type Trigger, episodeSchema, page, triggerSchema } from "@/lib/schemas";

const DURATIONS = [5, 15, 30, 60, 120] as const;

function useTriggers() {
  return useQuery({
    queryKey: keys.triggers,
    queryFn: () =>
      api("/triggers?include_archived=true&page_size=100", { schema: page(triggerSchema) }),
  });
}

function EpisodeLog({ triggers, exercises }: { triggers: Trigger[]; exercises: Exercise[] }) {
  const t = useTranslations("episodes");
  const format = useFormatter();
  const errorText = useErrorText();
  const toast = useToast();
  const queryClient = useQueryClient();
  const ids = { when: useId(), duration: useId(), trigger: useId(), helped: useId() };
  const [intensity, setIntensity] = useState<number | null>(null);
  const [earlier, setEarlier] = useState(false);
  const [when, setWhen] = useState("");
  const [duration, setDuration] = useState("");
  const [trigger, setTrigger] = useState("");
  const [helped, setHelped] = useState("");
  const [whatHelped, setWhatHelped] = useState("");
  const [missing, setMissing] = useState(false);

  const episodes = useQuery({
    queryKey: keys.episodes,
    queryFn: () => api("/episodes?page_size=50", { schema: page(episodeSchema) }),
  });
  const refresh = () => queryClient.invalidateQueries({ queryKey: keys.episodes });

  const save = useMutation({
    mutationFn: () =>
      api("/episodes", {
        method: "POST",
        body: {
          occurred_at: earlier && when ? new Date(when).toISOString() : new Date().toISOString(),
          intensity,
          duration_minutes: duration ? Number(duration) : null,
          trigger: trigger || null,
          helped_exercise: helped || null,
          what_helped: whatHelped.trim(),
        },
      }),
    onSuccess: () => {
      toast(t("log.saved"));
      setIntensity(null);
      setDuration("");
      setTrigger("");
      setHelped("");
      setWhatHelped("");
      setEarlier(false);
      void refresh();
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) => api(`/episodes/${id}`, { method: "DELETE" }),
    onSuccess: refresh,
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (intensity === null) setMissing(true);
    else save.mutate();
  };
  const labelOf = (id: string | null) => triggers.find((item) => item.id === id)?.label;
  const titleOf = (id: string | null) => exercises.find((item) => item.id === id)?.title;

  return (
    <div className="space-y-10">
      <form onSubmit={submit} noValidate className="space-y-6">
        <h2 className="h2">{t("log.title")}</h2>
        <ScaleControl
          label={t("log.intensity")}
          value={intensity}
          onChange={(value) => {
            setIntensity(value);
            setMissing(false);
          }}
          options={SCALE.map((value) => ({ value, name: t(`level.${value}`) }))}
          clearLabel={t("log.clear")}
        />
        <Toggle label={t("log.whenEarlier")} hint={t("log.whenNow")} checked={earlier} onChange={setEarlier} />
        {earlier ? (
          <div>
            <label htmlFor={ids.when} className="mb-1.5 block font-medium">
              {t("log.whenTime")}
            </label>
            <input
              id={ids.when}
              type="datetime-local"
              className="control"
              value={when}
              onChange={(event) => setWhen(event.target.value)}
            />
          </div>
        ) : null}
        <div>
          <label htmlFor={ids.duration} className="mb-1.5 block font-medium">
            {t("log.duration")}
          </label>
          <select
            id={ids.duration}
            className="control"
            value={duration}
            onChange={(event) => setDuration(event.target.value)}
          >
            <option value="">{t("log.durationUnset")}</option>
            {DURATIONS.map((minutes) => (
              <option key={minutes} value={minutes}>
                {minutes === 60 ? t("log.hour") : minutes > 60 ? t("log.longer") : t("log.minutes", { minutes })}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={ids.trigger} className="mb-1.5 block font-medium">
            {t("log.trigger")}
          </label>
          <select
            id={ids.trigger}
            className="control"
            value={trigger}
            onChange={(event) => setTrigger(event.target.value)}
          >
            <option value="">{t("log.triggerNone")}</option>
            {triggers
              .filter((item) => item.is_active)
              .map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
          </select>
        </div>
        {exercises.length > 0 ? (
          <div>
            <label htmlFor={ids.helped} className="mb-1.5 block font-medium">
              {t("log.helped")}
            </label>
            <select
              id={ids.helped}
              className="control"
              value={helped}
              onChange={(event) => setHelped(event.target.value)}
            >
              <option value="">{t("log.helpedNone")}</option>
              {exercises.map((exercise) => (
                <option key={exercise.id} value={exercise.id}>
                  {exercise.title}
                </option>
              ))}
            </select>
          </div>
        ) : null}
        <Field
          label={t("log.whatHelped")}
          hint={t("log.whatHelpedHint")}
          name="what_helped"
          maxLength={200}
          value={whatHelped}
          onChange={(event) => setWhatHelped(event.target.value)}
        />
        {missing ? (
          <Notice tone="attention" role="alert">
            {t("log.intensityRequired")}
          </Notice>
        ) : null}
        {save.isError ? (
          <Notice tone="attention" role="alert">
            {errorText(save.error)}
          </Notice>
        ) : null}
        <Button type="submit" busy={save.isPending}>
          {t("log.save")}
        </Button>
      </form>

      <section aria-labelledby="past-title">
        <h2 id="past-title" className="h2 mb-3">
          {t("past.title")}
        </h2>
        {episodes.data?.results.length ? (
          <ul className="frame divide-y divide-line">
            {episodes.data.results.map((episode) => {
              const moment = format.dateTime(new Date(episode.occurred_at), {
                dateStyle: "medium",
                timeStyle: "short",
              });
              return (
                <li key={episode.id} className="flex items-start justify-between gap-4 px-5 py-4">
                  <div>
                    <p className="data text-dim">{moment}</p>
                    <p>
                      {t("past.intensity", { value: episode.intensity })}
                      {episode.duration_minutes ? ` · ${t("past.duration", { minutes: episode.duration_minutes })}` : ""}
                    </p>
                    {labelOf(episode.trigger) ? (
                      <p className="text-dim">{t("past.trigger", { label: labelOf(episode.trigger) ?? "" })}</p>
                    ) : null}
                    {episode.what_helped || titleOf(episode.helped_exercise) ? (
                      <p className="text-dim">
                        {t("past.helped", {
                          text: [titleOf(episode.helped_exercise), episode.what_helped].filter(Boolean).join(", "),
                        })}
                      </p>
                    ) : null}
                  </div>
                  <button
                    type="button"
                    className="btn-text shrink-0 text-sm"
                    aria-label={t("past.deleteLabel", { when: moment })}
                    onClick={() => remove.mutate(episode.id)}
                  >
                    {t("past.delete")}
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="prose-width text-dim">{episodes.isError ? t("error") : t("past.empty")}</p>
        )}
      </section>
    </div>
  );
}

function TriggerManager({ triggers, exercises }: { triggers: Trigger[]; exercises: Exercise[] }) {
  const t = useTranslations("episodes.triggers");
  const errorText = useErrorText();
  const queryClient = useQueryClient();
  const [label, setLabel] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [showArchived, setShowArchived] = useState(false);
  const refresh = () => queryClient.invalidateQueries({ queryKey: keys.triggers });

  const add = useMutation({
    mutationFn: () => api("/triggers", { method: "POST", body: { label: label.trim() } }),
    onSuccess: () => {
      setLabel("");
      void refresh();
    },
    onError: (error) => setProblem(errorText(error)),
  });
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, unknown> }) =>
      api(`/triggers/${id}`, { method: "PATCH", body }),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (id: string) => api(`/triggers/${id}`, { method: "DELETE" }),
    onSuccess: refresh,
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setProblem(null);
    if (!label.trim()) setProblem(t("required"));
    else add.mutate();
  };
  const shown = triggers.filter((item) => item.is_active || showArchived);

  return (
    <div className="space-y-8">
      <p className="prose-width text-dim">{t("intro")}</p>
      <form onSubmit={submit} noValidate className="space-y-4">
        <Field
          label={t("label")}
          hint={t("labelHint")}
          name="label"
          maxLength={80}
          value={label}
          onChange={(event) => setLabel(event.target.value)}
          error={problem ?? undefined}
        />
        <Button type="submit" busy={add.isPending}>
          {t("save")}
        </Button>
      </form>

      <section aria-labelledby="triggers-title">
        <h2 id="triggers-title" className="h2 mb-3">
          {t("title")}
        </h2>
        {shown.length === 0 ? (
          <p className="prose-width text-dim">{t("empty")}</p>
        ) : (
          <ul className="frame divide-y divide-line">
            {shown.map((item) => (
              <li key={item.id} className="px-5 py-4">
                <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                  <p className="font-medium">
                    {item.label}
                    {item.is_active ? null : <span className="data ml-2 text-dim">{t("archived")}</span>}
                  </p>
                  <div className="flex gap-4">
                    <button
                      type="button"
                      className="btn-text text-sm"
                      aria-label={t(item.is_active ? "archiveLabel" : "restoreLabel", { label: item.label })}
                      onClick={() => update.mutate({ id: item.id, body: { is_active: !item.is_active } })}
                    >
                      {t(item.is_active ? "archive" : "restore")}
                    </button>
                    <button
                      type="button"
                      className="btn-text text-sm"
                      aria-label={t("deleteLabel", { label: item.label })}
                      onClick={() => remove.mutate(item.id)}
                    >
                      {t("delete")}
                    </button>
                  </div>
                </div>
                {item.is_active ? (
                  <fieldset className="mt-2">
                    <legend className="mb-1 text-sm text-dim">{t("preferred", { label: item.label })}</legend>
                    {exercises.length === 0 ? (
                      <p className="text-sm text-dim">{t("preferredNone")}</p>
                    ) : (
                      <div className="flex flex-wrap gap-x-5">
                        {exercises.map((exercise) => {
                          const chosen = item.preferred_exercise_ids.includes(exercise.id);
                          return (
                            <label key={exercise.id} className="flex min-h-11 cursor-pointer items-center gap-2">
                              <input
                                type="checkbox"
                                className="h-5 w-5 accent-(--accent-hi)"
                                checked={chosen}
                                onChange={() =>
                                  update.mutate({
                                    id: item.id,
                                    body: {
                                      preferred_exercise_ids: chosen
                                        ? item.preferred_exercise_ids.filter((id) => id !== exercise.id)
                                        : [...item.preferred_exercise_ids, exercise.id],
                                    },
                                  })
                                }
                              />
                              <span>{exercise.title}</span>
                            </label>
                          );
                        })}
                      </div>
                    )}
                  </fieldset>
                ) : null}
              </li>
            ))}
          </ul>
        )}
        {triggers.some((item) => !item.is_active) ? (
          <div className="mt-4">
            <Toggle label={t("showArchived")} checked={showArchived} onChange={setShowArchived} />
          </div>
        ) : null}
      </section>
    </div>
  );
}

export default function EpisodesPage() {
  const t = useTranslations("episodes");
  const triggers = useTriggers();
  const exercises = useExercises();
  const triggerList = triggers.data?.results ?? [];
  const exerciseList = exercises.data?.results ?? [];
  return (
    <div>
      <h1 className="h1 mb-3">{t("title")}</h1>
      <p className="prose-width mb-8 text-dim">{t("intro")}</p>
      <Tabs
        label={t("tabs")}
        tabs={[
          { id: "log", title: t("logTab"), content: <EpisodeLog triggers={triggerList} exercises={exerciseList} /> },
          {
            id: "triggers",
            title: t("triggersTab"),
            content: <TriggerManager triggers={triggerList} exercises={exerciseList} />,
          },
        ]}
      />
    </div>
  );
}
