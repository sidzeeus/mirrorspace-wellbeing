"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { type FormEvent, useId, useState } from "react";

import { Dialog, useToast } from "@/components/ui/controls";
import { Button, Notice } from "@/components/ui/primitives";
import { ApiError, api } from "@/lib/api";
import { useErrorText } from "@/lib/hooks";
import { clearOfflineCopies, saveOfflinePlan, useOfflinePlan, useOfflineResources } from "@/lib/offline";
import { type Resource, type SafetyPlan, safetyPlanSchema } from "@/lib/schemas";

const SECTIONS = ["warning_signs", "coping_steps", "people"] as const;
type Section = (typeof SECTIONS)[number];

const toLines = (text: string) =>
  text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

function PlanEditor({
  plan,
  resources,
  onDone,
}: {
  plan: SafetyPlan;
  resources: Resource[];
  onDone: () => void;
}) {
  const t = useTranslations("plan");
  const errorText = useErrorText();
  const toast = useToast();
  const queryClient = useQueryClient();
  const baseId = useId();
  const [text, setText] = useState<Record<Section, string>>({
    warning_signs: plan.warning_signs.join("\n"),
    coping_steps: plan.coping_steps.join("\n"),
    people: plan.people.join("\n"),
  });
  const [chosen, setChosen] = useState<string[]>(plan.resource_ids);

  const save = useMutation({
    mutationFn: () =>
      api("/safety-plan", {
        method: "PUT",
        body: {
          warning_signs: toLines(text.warning_signs),
          coping_steps: toLines(text.coping_steps),
          people: toLines(text.people),
          resource_ids: chosen,
        },
        schema: safetyPlanSchema,
      }),
    onSuccess: (saved) => {
      // Keep the device copy in step, so Support shows the new plan offline.
      saveOfflinePlan(saved);
      queryClient.setQueryData(["offline", "plan"], { data: saved, savedAt: null });
      toast(t("saved"));
      onDone();
    },
  });
  const fieldError = (section: Section) =>
    save.error instanceof ApiError ? save.error.field(section) : undefined;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    save.mutate();
  };

  return (
    <form onSubmit={submit} noValidate className="space-y-6">
      {SECTIONS.map((section) => (
        <div key={section}>
          <label htmlFor={`${baseId}-${section}`} className="mb-1.5 block font-medium">
            {t(section)}
          </label>
          <p id={`${baseId}-${section}-hint`} className="mb-1.5 text-sm text-dim">
            {t(`${section}Hint`)}
          </p>
          <textarea
            id={`${baseId}-${section}`}
            aria-describedby={`${baseId}-${section}-hint`}
            aria-invalid={fieldError(section) ? true : undefined}
            rows={4}
            className="control"
            value={text[section]}
            onChange={(event) => setText({ ...text, [section]: event.target.value })}
          />
          {fieldError(section) ? (
            <p role="alert" className="mt-1.5 text-sm text-warm">
              {t("limit")}
            </p>
          ) : null}
        </div>
      ))}
      <fieldset>
        <legend className="mb-1.5 font-medium">{t("resources")}</legend>
        {resources.length === 0 ? (
          <p className="text-sm text-dim">{t("resourcesNone")}</p>
        ) : (
          resources.map((resource) => (
            <label key={resource.id} className="flex min-h-11 cursor-pointer items-center gap-3">
              <input
                type="checkbox"
                className="h-5 w-5 accent-(--accent-hi)"
                checked={chosen.includes(resource.id)}
                onChange={(event) =>
                  setChosen(
                    event.target.checked
                      ? [...chosen, resource.id]
                      : chosen.filter((id) => id !== resource.id),
                  )
                }
              />
              <span>
                {resource.name} <span className="data text-dim">{resource.phone}</span>
              </span>
            </label>
          ))
        )}
      </fieldset>
      {save.isError && !SECTIONS.some(fieldError) ? (
        <Notice tone="attention" role="alert">
          {errorText(save.error)}
        </Notice>
      ) : null}
      <div className="flex flex-wrap gap-3">
        <Button type="submit" busy={save.isPending}>
          {t("save")}
        </Button>
        <Button variant="quiet" onClick={onDone}>
          {t("cancel")}
        </Button>
      </div>
    </form>
  );
}

export default function PlanPage() {
  const t = useTranslations("plan");
  const common = useTranslations("common");
  const format = useFormatter();
  const errorText = useErrorText();
  const queryClient = useQueryClient();
  const plan = useOfflinePlan();
  const resources = useOfflineResources();
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const remove = useMutation({
    mutationFn: () => api("/safety-plan", { method: "DELETE" }),
    onSuccess: () => {
      clearOfflineCopies();
      setConfirming(false);
      void queryClient.invalidateQueries({ queryKey: ["offline", "plan"] });
    },
  });

  const data = plan.data?.data;
  const offline = Boolean(plan.data?.savedAt);
  const resourceList = resources.data?.data ?? [];
  const empty = data
    ? SECTIONS.every((section) => data[section].length === 0) && data.resource_ids.length === 0
    : true;
  const date = (iso: string) => format.dateTime(new Date(iso), { dateStyle: "medium" });

  return (
    <div>
      <h1 className="h1 mb-3">{t("title")}</h1>
      <p className="prose-width mb-2 text-dim no-print">{t("intro")}</p>
      <p className="data mb-8 text-dim no-print">{t("private")}</p>

      {plan.isError ? (
        <Notice tone="attention" role="alert">
          <p>{t("error")}</p>
          <p className="text-dim">{errorText(plan.error)}</p>
          <button type="button" className="btn-text" onClick={() => void plan.refetch()}>
            {common("tryAgain")}
          </button>
        </Notice>
      ) : !data ? (
        <p role="status" className="text-dim">
          {common("loading")}
        </p>
      ) : editing ? (
        <PlanEditor plan={data} resources={resourceList} onDone={() => setEditing(false)} />
      ) : (
        <>
          {offline && plan.data?.savedAt ? (
            <div className="mb-6">
              <Notice tone="attention" role="status">
                {t("offlineCopy", { date: date(plan.data.savedAt) })}
              </Notice>
            </div>
          ) : null}
          {empty ? (
            <p className="prose-width mb-6 text-dim">{t("empty")}</p>
          ) : (
            <div className="frame mb-4 divide-y divide-line" data-plan-view>
              {SECTIONS.map((section) => (
                <section key={section} className="p-5">
                  <h2 className="mb-2 font-medium">{t(section)}</h2>
                  {data[section].length > 0 ? (
                    <ul className="list-disc space-y-1 pl-5">
                      {data[section].map((line, index) => (
                        <li key={index}>{line}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-dim">{t("emptySection")}</p>
                  )}
                </section>
              ))}
              {data.resource_ids.length > 0 ? (
                <section className="p-5">
                  <h2 className="mb-2 font-medium">{t("resources")}</h2>
                  <ul className="space-y-1">
                    {resourceList
                      .filter((resource) => data.resource_ids.includes(resource.id))
                      .map((resource) => (
                        <li key={resource.id}>
                          {resource.name}{" "}
                          <a href={`tel:${resource.phone.replace(/\s+/g, "")}`} className="data link">
                            {resource.phone}
                          </a>
                        </li>
                      ))}
                  </ul>
                </section>
              ) : null}
            </div>
          )}
          {data.updated_at ? (
            <p className="data mb-6 text-dim">{t("updated", { date: date(data.updated_at) })}</p>
          ) : null}
          <div className="flex flex-wrap gap-3 no-print">
            <Button disabled={offline} onClick={() => setEditing(true)}>
              {empty ? t("start") : t("edit")}
            </Button>
            {empty ? null : (
              <>
                <Button variant="quiet" onClick={() => window.print()}>
                  {t("print")}
                </Button>
                <Button variant="quiet" disabled={offline} onClick={() => setConfirming(true)}>
                  {t("delete")}
                </Button>
              </>
            )}
          </div>
        </>
      )}

      <Dialog open={confirming} onOpenChange={setConfirming} title={t("delete")} description={t("deleteConfirm")}>
        <div className="flex flex-wrap gap-3">
          <Button variant="care" busy={remove.isPending} onClick={() => remove.mutate()}>
            {t("deleteYes")}
          </Button>
          <Button variant="quiet" onClick={() => setConfirming(false)}>
            {t("deleteNo")}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
