import { Scene } from "@/components/scene/Scene";
import type { SceneName } from "@/components/scene/fields";

export type StoryStep = { title: string; body: string; lumen: string };

const SCENES: readonly SceneName[] = ["point", "figure", "pair"];

/**
 * The three-part promise. Each step is a framed picture beside a few plain lines:
 * a point of light, the light as a person, two people together. The pictures are
 * still images first; they shimmer only where motion is allowed.
 */
export function Story({ steps }: { steps: readonly StoryStep[] }) {
  return (
    <ol data-story>
      {steps.map((step, index) => (
        <li
          key={step.title}
          className="grid items-center gap-8 border-b border-line py-14 lg:grid-cols-2 lg:gap-20 lg:py-24"
        >
          <div className={`marks border border-line ${index % 2 === 1 ? "lg:order-last" : ""}`}>
            <Scene scene={SCENES[index] ?? "point"} label={step.lumen} className="aspect-[4/3]" />
          </div>
          <div>
            <p className="label mb-5 text-dim" aria-hidden="true">
              {String(index + 1).padStart(2, "0")} / {String(steps.length).padStart(2, "0")}
            </p>
            <h3 className="h1 mb-5">{step.title}</h3>
            <p className="prose-width text-lg text-dim">{step.body}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
