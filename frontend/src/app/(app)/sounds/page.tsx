"use client";

import { useTranslations } from "next-intl";
import { useEffect, useId, useState, useSyncExternalStore } from "react";

import { Slider } from "@/components/ui/controls";
import { ambient, type Program } from "@/lib/ambient";

const TRACKS: readonly { program: Exclude<Program, "background">; tint: string }[] = [
  { program: "sleep", tint: "from-[#2d2584]/60" },
  { program: "relax", tint: "from-[#1b5f66]/60" },
  { program: "calm", tint: "from-[#5e3184]/60" },
];
const TIMERS = [0, 15, 30, 60] as const;

const noServer = () => "off";

/**
 * Calming sounds, made on this device: soft piano and rain for sleep, gentle piano to
 * relax, and slow waves to breathe along with. Nothing is downloaded. They are
 * offered as something pleasant to listen to, not as a treatment.
 */
export default function SoundsPage() {
  const t = useTranslations("sounds");
  const timerId = useId();
  const playing = useSyncExternalStore(ambient.subscribe, ambient.snapshot, noServer);
  const [volume, setVolume] = useState(80);
  const [minutes, setMinutes] = useState<(typeof TIMERS)[number]>(0);

  useEffect(() => ambient.setVolume(volume / 100), [volume]);

  // The sleep timer: fade out and stop after the chosen time.
  useEffect(() => {
    if (!minutes || playing === "off" || playing === "background") return;
    const timer = window.setTimeout(() => ambient.pause(), minutes * 60_000);
    return () => window.clearTimeout(timer);
  }, [minutes, playing]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="h1 mb-3">{t("title")}</h1>
        <p className="prose-width text-dim">{t("intro")}</p>
      </div>

      <ul className="grid gap-4 sm:grid-cols-3">
        {TRACKS.map(({ program, tint }) => {
          const on = playing === program;
          return (
            <li key={program} className={`frame flex flex-col bg-gradient-to-b ${tint} to-transparent p-5`}>
              <h2 className="h2 mb-1">{t(`tracks.${program}.title`)}</h2>
              <p className="mb-5 grow text-sm text-dim">{t(`tracks.${program}.body`)}</p>
              <button
                type="button"
                className={`btn ${on ? "btn-primary" : "btn-quiet"} w-full`}
                aria-pressed={on}
                onClick={() => (on ? ambient.pause() : ambient.play(program))}
                data-sound={program}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  {on ? <path d="M7 5h4v14H7zM13 5h4v14h-4z" /> : <path d="M8 5v14l11-7z" />}
                </svg>
                {on ? t("pause") : t("play", { name: t(`tracks.${program}.title`) })}
              </button>
              {on ? (
                <p className="mt-3 text-center text-xs text-dim" role="status">
                  {t("nowPlaying")}
                </p>
              ) : null}
            </li>
          );
        })}
      </ul>

      <section aria-labelledby="sound-settings" className="frame space-y-5 p-5">
        <h2 id="sound-settings" className="h2">
          {t("settings")}
        </h2>
        <Slider
          label={t("volume")}
          value={volume}
          onChange={setVolume}
          min={0}
          max={100}
          step={5}
          valueText={`${volume}%`}
        />
        <div>
          <label htmlFor={timerId} className="mb-1.5 block font-medium">
            {t("timer")}
          </label>
          <select
            id={timerId}
            className="control max-w-xs"
            value={minutes}
            onChange={(event) => setMinutes(Number(event.target.value) as (typeof TIMERS)[number])}
          >
            {TIMERS.map((value) => (
              <option key={value} value={value}>
                {value ? t("timerMinutes", { minutes: value }) : t("timerOff")}
              </option>
            ))}
          </select>
        </div>
        <p className="text-sm text-dim">{t("note")}</p>
      </section>
    </div>
  );
}
