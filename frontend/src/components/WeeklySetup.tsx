"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { useId, useState } from "react";

import { useToast } from "@/components/ui/controls";
import { Button, Notice, Panel } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { WEEKLY_PURPOSE } from "@/lib/constants";
import { keys, useErrorText } from "@/lib/hooks";
import { type Contact, weeklyPreviewSchema } from "@/lib/schemas";

// A Monday, used only to get weekday names in the person's language.
const MONDAY = Date.UTC(2024, 0, 1);
export function weekdayName(format: ReturnType<typeof useFormatter>, weekday: number): string {
  return format.dateTime(new Date(MONDAY + weekday * 86_400_000), {
    weekday: "long",
    timeZone: "UTC",
  });
}

/**
 * Turning the weekly note on, in three small steps: what is shared, the real message,
 * then the schedule and an explicit confirmation. Nothing is on until the last button.
 */
export function WeeklySetup({ contact, onClose }: { contact: Contact; onClose: () => void }) {
  const t = useTranslations("sharing.setup");
  const format = useFormatter();
  const errorText = useErrorText();
  const toast = useToast();
  const queryClient = useQueryClient();
  const ids = { weekday: useId(), hour: useId() };
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [weekday, setWeekday] = useState<number | null>(null);
  const [hour, setHour] = useState<number | null>(null);
  const [agreed, setAgreed] = useState(false);
  const [missing, setMissing] = useState(false);

  const preview = useQuery({
    queryKey: ["weekly-preview", contact.id],
    queryFn: () => api(`/sharing/preview?contact=${contact.id}`, { schema: weeklyPreviewSchema }),
    staleTime: 0,
  });
  const data = preview.data;

  const turnOn = useMutation({
    mutationFn: () =>
      api("/sharing/consent", {
        method: "POST",
        body: {
          purpose: WEEKLY_PURPOSE,
          contact: contact.id,
          notice_version: data?.notice_version,
          preview_hash: data?.preview_hash,
          confirmed: true,
          send_weekday: weekday ?? data?.default_schedule.send_weekday,
          send_hour: hour ?? data?.default_schedule.send_hour,
        },
      }),
    onSuccess: () => {
      toast(t("done"));
      void queryClient.invalidateQueries({ queryKey: keys.consents });
      onClose();
    },
  });

  if (preview.isError) {
    return (
      <Notice tone="attention" role="alert">
        <p>{errorText(preview.error)}</p>
        <Button variant="quiet" onClick={onClose}>
          {t("cancel")}
        </Button>
      </Notice>
    );
  }
  if (!data) return null;

  return (
    <Panel marks className="p-5" data-weekly-setup>
      <h3 className="h2 mb-1">{t("title", { name: contact.name })}</h3>
      <p className="data mb-5 text-dim" aria-live="polite">
        {t("step", { step })}
      </p>

      {step === 1 ? (
        <div className="space-y-5">
          <h4 className="font-medium">{t("sharedTitle")}</h4>
          <p className="text-dim">{data.notice.purpose}</p>
          {(
            [
              ["shared", data.notice.shared],
              ["neverShared", data.notice.never_shared],
              ["limits", data.notice.limits],
            ] as const
          ).map(([key, lines]) => (
            <div key={key}>
              <p className="mb-1 font-medium">{t(key)}</p>
              <ul className="list-disc space-y-1 pl-5 text-dim" data-notice={key}>
                {lines.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>
          ))}
          <p className="text-dim">{data.notice.control}</p>
        </div>
      ) : step === 2 ? (
        <div>
          <h4 className="mb-2 font-medium">{t("previewTitle")}</h4>
          <p className="mb-4 text-dim">{t("previewIntro", { name: contact.name })}</p>
          <dl className="frame divide-y divide-line">
            <div className="p-4">
              <dt className="text-sm text-dim">{t("to")}</dt>
              <dd data-preview-recipient>
                {data.recipient.name} <span className="data text-dim">({data.recipient.email})</span>
              </dd>
            </div>
            <div className="p-4">
              <dt className="text-sm text-dim">{t("subject")}</dt>
              <dd>{data.subject}</dd>
            </div>
            <div className="p-4">
              <dt className="text-sm text-dim">{t("message")}</dt>
              <dd className="whitespace-pre-wrap" data-preview-body>
                {data.body}
              </dd>
            </div>
          </dl>
        </div>
      ) : (
        <div className="space-y-5">
          <h4 className="font-medium">{t("confirmTitle")}</h4>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor={ids.weekday} className="mb-1.5 block font-medium">
                {t("weekday")}
              </label>
              <select
                id={ids.weekday}
                className="control"
                value={weekday ?? data.default_schedule.send_weekday}
                onChange={(event) => setWeekday(Number(event.target.value))}
              >
                {[0, 1, 2, 3, 4, 5, 6].map((day) => (
                  <option key={day} value={day}>
                    {weekdayName(format, day)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor={ids.hour} className="mb-1.5 block font-medium">
                {t("hour")}
              </label>
              <select
                id={ids.hour}
                className="control"
                value={hour ?? data.default_schedule.send_hour}
                onChange={(event) => setHour(Number(event.target.value))}
              >
                {Array.from({ length: 24 }, (_, value) => (
                  <option key={value} value={value}>
                    {t("hourOption", { hour: String(value).padStart(2, "0") })}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <label className="flex min-h-11 cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              className="mt-1 h-6 w-6 shrink-0 accent-(--lumen-hi)"
              checked={agreed}
              onChange={(event) => {
                setAgreed(event.target.checked);
                setMissing(false);
              }}
            />
            <span className="font-medium">{t("agree", { name: contact.name })}</span>
          </label>
          <p className="data text-dim">{t("version", { version: data.notice_version })}</p>
          {missing ? (
            <Notice tone="attention" role="alert">
              {t("agreeRequired")}
            </Notice>
          ) : null}
          {turnOn.isError ? (
            <Notice tone="attention" role="alert">
              {errorText(turnOn.error)}
            </Notice>
          ) : null}
        </div>
      )}

      <div className="mt-6 flex flex-wrap gap-3">
        {step < 3 ? (
          <Button onClick={() => setStep((step + 1) as 2 | 3)}>{t("next")}</Button>
        ) : (
          <Button
            busy={turnOn.isPending}
            onClick={() => (agreed ? turnOn.mutate() : setMissing(true))}
          >
            {t("turnOn")}
          </Button>
        )}
        {step > 1 ? (
          <Button variant="quiet" onClick={() => setStep((step - 1) as 1 | 2)}>
            {t("back")}
          </Button>
        ) : null}
        <Button variant="quiet" onClick={onClose}>
          {t("cancel")}
        </Button>
      </div>
    </Panel>
  );
}
