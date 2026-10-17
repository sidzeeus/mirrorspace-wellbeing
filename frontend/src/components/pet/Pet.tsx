/**
 * The pets: small animals sitting with their backs to you, drawn in SVG and animated
 * with CSS (globals.css, "Pets"). They breathe, twitch an ear, sway a tail, and react
 * to a mood. Nothing is downloaded: no images, no animation files, no third party.
 *
 * Every animation stops for reduced motion (the global rule in globals.css), and a pet
 * never carries information on its own: each one has a label saying what it shows.
 */
import type { CSSProperties } from "react";

export type Species = "cat" | "bunny" | "fox" | "mouse";
/** Colour choices, so the same animal can come in different coats. */
export type Coat = "pink" | "lilac" | "orange" | "grey" | "cream" | "teal" | "ginger";
export type PetMood =
  | "idle"
  | "listening"
  | "heavy"
  | "storm"
  | "racing"
  | "alone"
  | "lighter"
  | "steady";

export type PetProps = {
  /** What the picture shows, for screen readers. Leave out for a decorative pet. */
  label?: string;
  species?: Species;
  mood?: PetMood;
  /** Breath, 0 (out) to 1 (in). When set, the pet breathes exactly with it. */
  breathPhase?: number;
  /** A second, smaller pet sits beside this one. */
  companion?: boolean;
  /** A different coat from the animal's usual colour. */
  coat?: Coat;
  className?: string;
};

type Palette = { body: string; shade: string; inner: string; accent: string };

const COATS: Record<Coat, Palette> = {
  pink: { body: "#f472b6", shade: "#ec4899", inner: "#fbcfe8", accent: "#fdf2f8" },
  lilac: { body: "#c4b5fd", shade: "#a78bfa", inner: "#f5d0fe", accent: "#ffffff" },
  orange: { body: "#fb923c", shade: "#f97316", inner: "#fed7aa", accent: "#fff7ed" },
  grey: { body: "#b8b4c8", shade: "#9690ab", inner: "#fbcfe8", accent: "#f1f0f5" },
  cream: { body: "#f3e3c3", shade: "#e2c999", inner: "#fbcfe8", accent: "#ffffff" },
  teal: { body: "#7fd6c2", shade: "#4fb8a2", inner: "#d1f5ec", accent: "#f0fdfa" },
  ginger: { body: "#f59e0b", shade: "#d97706", inner: "#fde68a", accent: "#fffbeb" },
};
const USUAL: Record<Species, Coat> = { cat: "pink", bunny: "lilac", fox: "orange", mouse: "grey" };

const COMPANION: Record<Species, Species> = { cat: "bunny", bunny: "cat", fox: "bunny", mouse: "cat" };

function Ears({ species, colors }: { species: Species; colors: Palette }) {
  if (species === "mouse") {
    return (
      <>
        <g className="pet-ear pet-ear-l">
          <circle cx="72" cy="34" r="20" fill={colors.body} />
          <circle cx="72" cy="34" r="12" fill={colors.inner} />
        </g>
        <g className="pet-ear pet-ear-r">
          <circle cx="128" cy="34" r="20" fill={colors.body} />
          <circle cx="128" cy="34" r="12" fill={colors.inner} />
        </g>
      </>
    );
  }
  if (species === "bunny") {
    return (
      <>
        <g className="pet-ear pet-ear-l">
          <ellipse cx="86" cy="22" rx="10" ry="30" transform="rotate(-12 86 22)" fill={colors.body} />
          <ellipse cx="86" cy="24" rx="5" ry="22" transform="rotate(-12 86 24)" fill={colors.inner} />
        </g>
        <g className="pet-ear pet-ear-r">
          <ellipse cx="114" cy="22" rx="10" ry="30" transform="rotate(12 114 22)" fill={colors.body} />
          <ellipse cx="114" cy="24" rx="5" ry="22" transform="rotate(12 114 24)" fill={colors.inner} />
        </g>
      </>
    );
  }
  const tip = species === "fox" ? "#431407" : colors.inner;
  return (
    <>
      <g className="pet-ear pet-ear-l">
        <path d="M74 52 L70 14 L98 40 Z" fill={colors.body} />
        <path d="M76 44 L74 22 L90 38 Z" fill={tip} opacity={species === "fox" ? 0.9 : 1} />
      </g>
      <g className="pet-ear pet-ear-r">
        <path d="M126 52 L130 14 L102 40 Z" fill={colors.body} />
        <path d="M124 44 L126 22 L110 38 Z" fill={tip} opacity={species === "fox" ? 0.9 : 1} />
      </g>
    </>
  );
}

function Tail({ species, colors }: { species: Species; colors: Palette }) {
  if (species === "mouse") {
    return (
      <g className="pet-tail">
        <path
          d="M126 174 C 170 182 186 150 168 136 C 156 128 150 146 162 150"
          fill="none"
          stroke={colors.inner}
          strokeWidth="4"
          strokeLinecap="round"
        />
      </g>
    );
  }
  if (species === "bunny") {
    return (
      <g className="pet-tail">
        <circle cx="100" cy="168" r="12" fill={colors.accent} />
      </g>
    );
  }
  if (species === "fox") {
    return (
      <g className="pet-tail">
        <path
          d="M126 170 C 158 176 182 156 176 128 C 172 110 156 106 150 118 C 160 130 156 152 126 160 Z"
          fill={colors.body}
        />
        <path d="M176 128 C 172 110 156 106 150 118 C 158 120 166 124 176 128 Z" fill={colors.accent} />
      </g>
    );
  }
  return (
    <g className="pet-tail">
      <path
        d="M126 172 C 160 178 174 152 162 134 C 156 124 162 112 172 116"
        fill="none"
        stroke={colors.body}
        strokeWidth="11"
        strokeLinecap="round"
      />
      <path d="M162 134 C 156 124 162 112 172 116" fill="none" stroke={colors.shade} strokeWidth="11" strokeLinecap="round" />
    </g>
  );
}

/** One animal. Kept separate so a companion can be drawn with the same parts. */
function Animal({ species, coat }: { species: Species; coat?: Coat }) {
  const colors = COATS[coat ?? USUAL[species]];
  const round = species === "bunny" || species === "mouse";
  return (
    <g className="pet-animal">
      <Tail species={species} colors={colors} />
      <g className="pet-body">
        <ellipse cx="70" cy="166" rx="24" ry="16" fill={colors.shade} />
        <ellipse cx="130" cy="166" rx="24" ry="16" fill={colors.shade} />
        <path
          d={
            round
              ? "M100 72 C 64 72 52 104 52 134 C 52 162 68 180 100 180 C 132 180 148 162 148 134 C 148 104 136 72 100 72 Z"
              : "M100 70 C 72 70 58 100 56 130 C 54 158 66 180 100 180 C 134 180 146 158 144 130 C 142 100 128 70 100 70 Z"
          }
          fill={colors.body}
        />
        {/* Light falling on the back from the left. */}
        <ellipse cx="82" cy="116" rx="12" ry="30" fill="#ffffff" opacity="0.16" />
        <g className="pet-head">
          <Ears species={species} colors={colors} />
          <circle cx="100" cy="62" r="30" fill={colors.body} />
          <ellipse cx="90" cy="52" rx="9" ry="12" fill="#ffffff" opacity="0.14" />
        </g>
      </g>
    </g>
  );
}

export function Pet({
  label,
  species = "cat",
  mood = "idle",
  breathPhase,
  companion = false,
  coat,
  className = "",
}: PetProps) {
  const guided = breathPhase !== undefined;
  const breath = guided ? 0.9 + 0.18 * Math.max(0, Math.min(1, breathPhase)) : 1;
  const style = guided ? ({ "--pet-breath": breath } as CSSProperties) : undefined;
  const second = COMPANION[species];
  return (
    <div
      {...(label ? { role: "img", "aria-label": label } : { "aria-hidden": true })}
      data-pet={species}
      data-mood={mood}
      className={`pet relative aspect-square ${className}`}
    >
      <svg viewBox="0 0 200 200" className="h-full w-full overflow-visible" aria-hidden="true">
        <ellipse cx="100" cy="184" rx="58" ry="7" fill="#000000" opacity="0.22" />
        {companion ? (
          <g className="pet-companion">
            <g transform="translate(112 86) scale(0.5)">
              <Animal species={second} />
            </g>
          </g>
        ) : null}
        <g
          className={`pet-main ${guided ? "pet-guided" : ""}`}
          style={style}
          transform={companion ? "translate(4 38) scale(0.76)" : undefined}
        >
          <Animal species={species} coat={coat} />
        </g>
      </svg>
    </div>
  );
}
