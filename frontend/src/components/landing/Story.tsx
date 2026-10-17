import { Pet, type PetMood, type Species } from "@/components/pet/Pet";

export type StoryStep = { title: string; body: string; pet: string };

const PETS: readonly { species: Species; mood: PetMood; companion?: boolean }[] = [
  { species: "cat", mood: "listening" },
  { species: "bunny", mood: "racing" },
  { species: "fox", mood: "alone", companion: true },
];

/**
 * The three-part promise, as three glass cards, each with a pet: one listening, one
 * breathing slowly, one joined by a friend.
 */
export function Story({ steps }: { steps: readonly StoryStep[] }) {
  return (
    <ol data-story className="grid gap-5 md:grid-cols-3">
      {steps.map((step, index) => {
        const pet = PETS[index] ?? PETS[0]!;
        return (
          <li key={step.title} className="frame flex flex-col p-6">
            <Pet
              label={step.pet}
              species={pet.species}
              mood={pet.mood}
              companion={pet.companion}
              className="mx-auto mb-4 w-32"
            />
            <p className="label mb-2 text-dim" aria-hidden="true">
              {String(index + 1).padStart(2, "0")}
            </p>
            <h3 className="h2 mb-3">{step.title}</h3>
            <p className="text-dim">{step.body}</p>
          </li>
        );
      })}
    </ol>
  );
}
