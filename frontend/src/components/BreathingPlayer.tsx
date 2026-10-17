"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { Pet } from "@/components/pet/Pet";
import { Toggle } from "@/components/ui/controls";
import { Button, IconButton, Panel, ProgressRing } from "@/components/ui/primitives";
import { useLowBandwidth, useReducedMotion } from "@/lib/prefs";

const LIMITS = { inhale: [2, 8], exhale: [3, 10] } as const;

type Breath = { inhaling: boolean; progress: number; secondsLeft: number; elapsed: number };
const REST: Breath = { inhaling: true, progress: 0, secondsLeft: 0, elapsed: 0 };

/** A soft tone, made in the browser. No audio file is downloaded. */
function tone(context: AudioContext, frequency: number): void {
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.type = "sine";
  oscillator.frequency.value = frequency;
  gain.gain.setValueAtTime(0.0001, context.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.08, context.currentTime + 0.08);
  gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.9);
  oscillator.connect(gain).connect(context.destination);
  oscillator.start();
  oscillator.stop(context.currentTime + 1);
}

/**
 * Paced breathing. A bunny grows on the in-breath and settles on the out-breath
 * at a pace the person can change. With reduced motion or low-bandwidth mode, a
 * progress ring and words carry the same guidance. Sound and vibration are optional
 * and off until chosen. "End" is always available.
 */
export function BreathingPlayer({
  inhale: initialInhale,
  exhale: initialExhale,
  minutes,
  onFinish,
}: {
  inhale: number;
  exhale: number;
  minutes: number;
  onFinish: () => void;
}) {
  const t = useTranslations("exercises.breathing");
  const still = useReducedMotion();
  const low = useLowBandwidth();
  const [inhale, setInhale] = useState(initialInhale);
  const [exhale, setExhale] = useState(initialExhale);
  const [running, setRunning] = useState(false);
  const [started, setStarted] = useState(false);
  const [sound, setSound] = useState(false);
  const [haptic, setHaptic] = useState(false);
  const [breath, setBreath] = useState<Breath>(REST);
  const audio = useRef<AudioContext | null>(null);
  const cues = useRef({ sound, haptic });
  const finish = useRef(onFinish);
  useEffect(() => {
    cues.current = { sound, haptic };
    finish.current = onFinish;
  });

  const total = minutes * 60;
  const useRing = still || low;

  useEffect(() => {
    if (!running) return;
    const cycle = inhale + exhale;
    let last = performance.now();
    let elapsed = 0;
    let wasInhaling: boolean | null = null;
    let handle = 0;
    let timer: ReturnType<typeof setInterval> | undefined;

    const tick = () => {
      const now = performance.now();
      elapsed += (now - last) / 1000;
      last = now;
      if (elapsed >= total) {
        finish.current();
        return false;
      }
      const position = elapsed % cycle;
      const inhaling = position < inhale;
      if (inhaling !== wasInhaling) {
        wasInhaling = inhaling;
        if (cues.current.sound && audio.current) tone(audio.current, inhaling ? 392 : 294);
        if (cues.current.haptic) navigator.vibrate?.(inhaling ? 60 : [40, 60, 40]);
      }
      setBreath({
        inhaling,
        progress: inhaling ? position / inhale : (position - inhale) / exhale,
        secondsLeft: Math.ceil(inhaling ? inhale - position : cycle - position),
        elapsed,
      });
      return true;
    };

    if (useRing) {
      // No animation frames: a quiet update four times a second is enough for text.
      timer = setInterval(() => {
        if (!tick()) clearInterval(timer);
      }, 250);
    } else {
      const loop = () => {
        if (tick()) handle = requestAnimationFrame(loop);
      };
      handle = requestAnimationFrame(loop);
    }
    return () => {
      cancelAnimationFrame(handle);
      clearInterval(timer);
    };
  }, [running, inhale, exhale, total, useRing]);

  useEffect(() => () => void audio.current?.close(), []);

  const toggleSound = (on: boolean) => {
    setSound(on);
    if (on && !audio.current) {
      const Context = window.AudioContext;
      if (Context) audio.current = new Context();
    }
    void audio.current?.resume();
  };

  const state = !started ? t("ready") : breath.inhaling ? t("in") : t("out");
  const phase = breath.inhaling ? breath.progress : 1 - breath.progress;
  const left = Math.max(0, Math.ceil(total - breath.elapsed));
  const change = (key: "inhale" | "exhale", delta: number) => {
    const [min, max] = LIMITS[key];
    const set = key === "inhale" ? setInhale : setExhale;
    set((value) => Math.max(min, Math.min(max, value + delta)));
  };

  return (
    <div className="mx-auto flex w-full max-w-md flex-col items-center gap-6">
      {useRing ? (
        <ProgressRing
          value={started ? phase : 0}
          label={t("ring", { state, seconds: breath.secondsLeft })}
          size={220}
        >
          <p className="h2">{state}</p>
          {started ? <p className="data text-dim">{breath.secondsLeft}</p> : null}
        </ProgressRing>
      ) : (
        <Panel className="w-full max-w-[16rem] p-6">
          <Pet label={t("lumen", { state })} species="bunny" breathPhase={started ? phase : 0.2} />
        </Panel>
      )}
      {useRing ? null : (
        <p className="h2" aria-hidden="true">
          {state}
        </p>
      )}
      {/* Announced once per phase, not once per frame. */}
      <p className="sr-only" role="status">
        {started ? state : ""}
      </p>
      <p className="data text-dim">
        {t("remaining", {
          minutes: Math.floor(left / 60),
          seconds: String(left % 60).padStart(2, "0"),
        })}
      </p>

      <Button
        className="w-full"
        onClick={() => {
          setStarted(true);
          setRunning((value) => !value);
        }}
      >
        {!started ? t("start") : running ? t("pause") : t("resume")}
      </Button>

      <fieldset className="w-full">
        <legend className="mb-2 font-medium">{t("pace")}</legend>
        {(
          [
            ["inhale", inhale, "inSeconds", "shorterIn", "longerIn"],
            ["exhale", exhale, "outSeconds", "shorterOut", "longerOut"],
          ] as const
        ).map(([key, value, text, shorter, longer]) => (
          <div key={key} className="flex min-h-12 items-center justify-between gap-3">
            <span aria-live="polite">{t(text, { seconds: value })}</span>
            <span className="flex gap-2">
              <IconButton label={t(shorter)} onClick={() => change(key, -1)}>
                −
              </IconButton>
              <IconButton label={t(longer)} onClick={() => change(key, 1)}>
                +
              </IconButton>
            </span>
          </div>
        ))}
      </fieldset>

      <div className="w-full space-y-1">
        <Toggle label={t("sound")} hint={t("soundHint")} checked={sound} onChange={toggleSound} />
        <Toggle label={t("haptic")} hint={t("hapticHint")} checked={haptic} onChange={setHaptic} />
      </div>
      <p className="text-center text-sm text-dim">{t("stopNote")}</p>
    </div>
  );
}
