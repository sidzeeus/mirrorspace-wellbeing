"use client";

import { useQuery } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";

import { type Metric, TrendChart } from "@/components/TrendChart";
import { Notice, Panel } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { keys, useErrorText } from "@/lib/hooks";
import { patternsSchema } from "@/lib/schemas";

const RANGES = [7, 28, 90] as const;
const METRICS: readonly Metric[] = ["mood", "sleep_hours", "sleep_quality", "energy", "stress"];

function Choice<T extends string | number>({
  legend,
  options,
  value,
  onChange,
  text,
}: {
  legend: string;
  options: readonly T[];
  value: T;
  onChange: (value: T) => void;
  text: (option: T) => string;
}) {
  return (
    <fieldset>
      <legend className="mb-2 font-medium">{legend}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={option === value}
            onClick={() => onChange(option)}
            className={`min-h-11 rounded-[14px] border px-4 ${
              option === value
                ? "border-lumen-hi bg-lumen-hi text-on-lumen"
                : "border-line-strong bg-surface hover:bg-raised"
            }`}
          >
            {text(option)}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

export default function PatternsPage() {
  const t = useTranslations("patterns");
  const common = useTranslations("common");
  const format = useFormatter();
  const errorText = useErrorText();
  const [days, setDays] = useState<(typeof RANGES)[number]>(28);
  const [metric, setMetric] = useState<Metric>("mood");

  const patterns = useQuery({
    queryKey: keys.patterns(days),
    queryFn: () => api(`/patterns?days=${days}`, { schema: patternsSchema }),
  });
  const data = patterns.data;
  const values = (data?.series ?? [])
    .map((point) => point[metric])
    .filter((value): value is number => value !== null);
  const day = (date: string) =>
    format.dateTime(new Date(`${date}T12:00:00Z`), { dateStyle: "medium", timeZone: "UTC" });

  return (
    <div>
      <h1 className="h1 mb-3">{t("title")}</h1>
      <p className="prose-width mb-8 text-dim">{t("intro")}</p>

      <div className="mb-8 space-y-5">
        <Choice
          legend={t("range")}
          options={RANGES}
          value={days}
          onChange={setDays}
          text={(option) => t("days", { days: option })}
        />
        <Choice
          legend={t("metric")}
          options={METRICS}
          value={metric}
          onChange={setMetric}
          text={(option) => t(`metrics.${option}`)}
        />
      </div>

      {patterns.isError ? (
        <Notice tone="attention" role="alert">
          <p>{t("error")}</p>
          <p className="text-dim">{errorText(patterns.error)}</p>
          <button type="button" className="btn-text" onClick={() => void patterns.refetch()}>
            {common("tryAgain")}
          </button>
        </Notice>
      ) : !data ? (
        <p role="status" className="text-dim">
          {common("loading")}
        </p>
      ) : (
        <>
          <Panel className="mb-4 p-3 sm:p-5">
            <TrendChart
              series={data.series}
              metric={metric}
              from={data.range.from}
              days={data.range.days}
              label={t("chart", {
                metric: t(`metrics.${metric}`),
                days: data.range.days,
                count: values.length,
                min: values.length ? Math.min(...values) : 0,
                max: values.length ? Math.max(...values) : 0,
              })}
            />
          </Panel>

          {data.series.length === 0 ? (
            <p className="prose-width mb-8 text-dim">{t("empty")}</p>
          ) : (
            <details className="mb-8">
              <summary className="link inline-flex min-h-11 cursor-pointer items-center">
                {t("table")}
              </summary>
              <div className="mt-3 overflow-x-auto">
                <table className="data w-full border-collapse text-left">
                  <thead>
                    <tr className="border-b border-line-strong">
                      <th scope="col" className="py-2 pr-4 font-normal text-dim">
                        {t("date")}
                      </th>
                      {METRICS.map((name) => (
                        <th key={name} scope="col" className="py-2 pr-4 font-normal text-dim">
                          {t(`metrics.${name}`)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.series.map((point) => (
                      <tr key={point.local_date} className="border-b border-line">
                        <th scope="row" className="whitespace-nowrap py-2 pr-4 font-normal">
                          {day(point.local_date)}
                        </th>
                        {METRICS.map((name) => (
                          <td key={name} className="py-2 pr-4">
                            {point[name] ?? <span className="sr-only">{t("notAnswered")}</span>}
                            {point[name] === null ? <span aria-hidden="true">·</span> : null}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          )}

          <section aria-labelledby="observations-title">
            <h2 id="observations-title" className="h2 mb-3">
              {t("observationsTitle")}
            </h2>
            <ul className="frame mb-4 divide-y divide-line">
              {data.observations.map((observation) => (
                <li key={observation.code} className="px-5 py-4" data-observation={observation.code}>
                  {t.has(`observations.${observation.code}`)
                    ? t(`observations.${observation.code}`, observation.params)
                    : observation.text}
                </li>
              ))}
            </ul>
            <p className="prose-width text-sm text-dim">{t("note")}</p>
          </section>
        </>
      )}
    </div>
  );
}
