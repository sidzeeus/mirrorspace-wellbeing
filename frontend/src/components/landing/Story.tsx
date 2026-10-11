"use client";

import { useEffect, useRef, useState } from "react";

import { Lumen } from "@/components/lumen/Lumen";
import type { LumenMode } from "@/components/lumen/shapes";
import { useLowBandwidth, useReducedMotion } from "@/lib/prefs";

export type StoryStep = { title: string; body: string; lumen: string };

const MODES: readonly LumenMode[] = ["orb", "figure", "pair"];
const DENSITY = [0.12, 0.85, 1] as const;

/**
 * The three-part promise. With motion allowed, one framed stage stays in view and the
 * light changes form as each step scrolls past. With reduced motion, low-bandwidth
 * mode or no JavaScript, each step simply has its own still image.
 */
export function Story({ steps }: { steps: readonly StoryStep[] }) {
  const still = useReducedMotion();
  const low = useLowBandwidth();
  const scrollDriven = !still && !low;
  const [active, setActive] = useState(0);
  const items = useRef<(HTMLLIElement | null)[]>([]);

  useEffect(() => {
    if (!scrollDriven) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActive(Number((entry.target as HTMLElement).dataset.step));
        }
      },
      { rootMargin: "-45% 0px -45% 0px" },
    );
    items.current.forEach((item) => item && observer.observe(item));
    return () => observer.disconnect();
  }, [scrollDriven]);

  return (
    <div
      data-story={scrollDriven ? "scroll" : "still"}
      className="grid gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] lg:gap-20"
    >
      {scrollDriven ? (
        <div className="sticky top-16 z-10 -mx-5 bg-ink px-5 py-4 lg:top-24 lg:mx-0 lg:self-start lg:bg-transparent lg:p-0">
          <div className="marks mx-auto w-40 border border-line sm:w-56 lg:w-full lg:max-w-sm">
            <Lumen
              label={steps[active]?.lumen ?? ""}
              mode={MODES[active]}
              density={DENSITY[active]}
              intensity={0.9}
              hue={0.25 + active * 0.25}
            />
          </div>
        </div>
      ) : null}
      <ol className={scrollDriven ? "" : "lg:col-span-2"}>
        {steps.map((step, index) => (
          <li
            key={step.title}
            data-step={index}
            ref={(element) => {
              items.current[index] = element;
            }}
            className={`border-t border-line py-10 ${
              scrollDriven
                ? "lg:flex lg:min-h-[70vh] lg:flex-col lg:justify-center"
                : "grid gap-6 sm:grid-cols-[10rem_1fr] sm:items-center"
            }`}
          >
            {scrollDriven ? null : (
              <div className="w-40 border border-line">
                <Lumen
                  label={step.lumen}
                  mode={MODES[index]}
                  density={DENSITY[index]}
                  intensity={0.9}
                  hue={0.25 + index * 0.25}
                />
              </div>
            )}
            <div>
              <p className="data mb-3 text-dim" aria-hidden="true">
                {index + 1}
              </p>
              <h3 className="h1 mb-4">{step.title}</h3>
              <p className="prose-width text-lg text-dim">{step.body}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
