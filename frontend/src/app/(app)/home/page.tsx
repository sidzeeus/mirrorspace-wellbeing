"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";

import { PawWeek } from "@/components/pet/PawWeek";
import { Pet } from "@/components/pet/Pet";
import { Notice, Panel, UnreviewedBadge, buttonClass } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { keys, localDate, useErrorText, useExercises, useMe } from "@/lib/hooks";
import { checkInSchema, page } from "@/lib/schemas";

const DAYS = 7;

export default function HomePage() {
  const t = useTranslations("home");
  const common = useTranslations("common");
  const format = useFormatter();
  const errorText = useErrorText();
  const me = useMe();
  const zone = me.data?.timezone ?? "UTC";
  const dates = Array.from({ length: DAYS }, (_, index) => localDate(zone, index - (DAYS - 1)));
  const from = dates[0]!;
  const today = dates[DAYS - 1]!;

  const checkIns = useQuery({
    queryKey: keys.checkIns(from),
    queryFn: () => api(`/check-ins?from=${from}&page_size=10`, { schema: page(checkInSchema) }),
  });
  const exercises = useExercises();

  const done = new Set(checkIns.data?.results.map((row) => row.local_date));
  const lit = dates.map((date) => done.has(date));
  const litNames = dates
    .filter((date) => done.has(date))
    .map((date) => format.dateTime(new Date(`${date}T12:00:00Z`), { weekday: "long", timeZone: "UTC" }));
  const days = format.list(litNames, { type: "conjunction" });
  const count = litNames.length;
  const checkedInToday = done.has(today);

  // One suggestion, never a list: breathing first because it needs nothing else.
  const suggestion =
    exercises.data?.results.find((exercise) => exercise.category === "breathing") ??
    exercises.data?.results[0];

  return (
    <div className="space-y-10">
      <div className="flex items-end justify-between gap-4">
        <h1 className="h1">
          {me.data?.display_name ? t("hello", { name: me.data.display_name }) : t("helloPlain")}
        </h1>
        <Pet species="cat" mood="listening" className="w-20 shrink-0 sm:w-24" />
      </div>

      {checkIns.isError ? (
        <Notice tone="attention" role="alert">
          <p>{t("error")}</p>
          <p className="text-dim">{errorText(checkIns.error)}</p>
          <button type="button" className="btn-text" onClick={() => void checkIns.refetch()}>
            {common("tryAgain")}
          </button>
        </Notice>
      ) : null}

      <section aria-labelledby="today-title">
        <h2 id="today-title" className="h2 mb-3">
          {t("checkIn.title")}
        </h2>
        <p className="prose-width mb-4 text-dim">
          {checkIns.isPending ? common("loading") : checkedInToday ? t("checkIn.done") : t("checkIn.invite")}
        </p>
        <Link href="/check-in" className={buttonClass(checkedInToday ? "quiet" : "primary")}>
          {checkedInToday ? t("checkIn.change") : t("checkIn.start")}
        </Link>
      </section>

      <section aria-labelledby="week-title">
        <h2 id="week-title" className="h2 mb-3">
          {t("week.title")}
        </h2>
        <Panel className="mb-4 overflow-hidden">
          <div className="mx-auto max-w-md">
            <PawWeek lit={lit} label={t("week.lumen", { count, days })} />
          </div>
          <ol className="data grid grid-cols-7 border-t border-line text-center text-dim" aria-hidden="true">
            {dates.map((date) => (
              <li key={date} className="py-2">
                {format.dateTime(new Date(`${date}T12:00:00Z`), { weekday: "narrow", timeZone: "UTC" })}
              </li>
            ))}
          </ol>
        </Panel>
        <p className="mb-1">{t("week.summary", { count, days })}</p>
        <p className="prose-width mb-3 text-sm text-dim">{t("week.note")}</p>
        <Link href="/patterns" className="link inline-flex min-h-11 items-center">
          {t("week.patterns")}
        </Link>
      </section>

      <section aria-labelledby="step-title">
        <h2 id="step-title" className="h2 mb-3">
          {t("step.title")}
        </h2>
        {suggestion ? (
          <div className="frame p-5">
            <p className="mb-1 flex flex-wrap items-center gap-2 font-medium">
              {suggestion.title}
              {suggestion.reviewed ? null : <UnreviewedBadge>{common("unreviewed")}</UnreviewedBadge>}
            </p>
            <p className="mb-1 text-dim">{suggestion.summary}</p>
            <p className="data mb-4 text-dim">
              {t("step.minutes", { minutes: suggestion.duration_minutes })}
            </p>
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
              <Link href={`/exercises/${suggestion.id}`} className={buttonClass("quiet")}>
                {t("step.open")}
              </Link>
              <Link href="/exercises" className="link inline-flex min-h-11 items-center">
                {t("step.all")}
              </Link>
            </div>
          </div>
        ) : (
          <p className="prose-width text-dim">
            {exercises.isPending ? common("loading") : t("step.none")}
          </p>
        )}
      </section>

      <section aria-labelledby="quick-title">
        <h2 id="quick-title" className="h2 mb-3">
          {t("quick.title")}
        </h2>
        <div className="flex flex-wrap gap-3">
          <Link href="/plan" className={buttonClass("quiet")}>
            {t("quick.plan")}
          </Link>
          <a href="/support" className={buttonClass("quiet")}>
            {t("quick.support")}
          </a>
        </div>
      </section>
    </div>
  );
}
