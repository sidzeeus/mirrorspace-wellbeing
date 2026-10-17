import { type Coat, Pet, type PetMood, type Species } from "@/components/pet/Pet";

type Critter = { species: Species; coat: Coat; mood?: PetMood };

/**
 * A little pair of animals perched above each section's heading, in colours that
 * suit the section. Decoration only, hidden from screen readers. Home, Chat and Vent
 * have Sushi instead; Support has nothing, so it stays still and clear.
 */
const BY_SECTION: Record<string, readonly [Critter, Critter]> = {
  "/check-in": [{ species: "cat", coat: "ginger" }, { species: "mouse", coat: "grey" }],
  "/patterns": [{ species: "mouse", coat: "grey", mood: "listening" }, { species: "bunny", coat: "cream" }],
  "/episodes": [{ species: "bunny", coat: "lilac", mood: "steady" }, { species: "mouse", coat: "cream" }],
  "/exercises": [{ species: "fox", coat: "orange", mood: "racing" }, { species: "bunny", coat: "teal" }],
  "/plan": [{ species: "fox", coat: "orange", mood: "steady" }, { species: "cat", coat: "pink" }],
  "/sharing": [{ species: "cat", coat: "pink", mood: "listening" }, { species: "cat", coat: "ginger" }],
  "/sounds": [{ species: "bunny", coat: "lilac", mood: "heavy" }, { species: "mouse", coat: "cream" }],
  "/settings": [{ species: "mouse", coat: "grey" }, { species: "cat", coat: "cream", mood: "listening" }],
  "/resources": [{ species: "bunny", coat: "cream" }, { species: "fox", coat: "orange", mood: "steady" }],
  "/onboarding": [{ species: "cat", coat: "pink", mood: "listening" }, { species: "bunny", coat: "lilac" }],
};

export function SectionCritters({ pathname }: { pathname: string }) {
  const section = Object.keys(BY_SECTION).find(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );
  if (!section) return null;
  const [big, small] = BY_SECTION[section]!;
  return (
    <div aria-hidden="true" className="pointer-events-none flex h-16 items-end justify-end gap-0.5" data-critters>
      <Pet species={small.species} coat={small.coat} mood={small.mood} className="w-10" />
      <Pet species={big.species} coat={big.coat} mood={big.mood} className="w-16" />
    </div>
  );
}
