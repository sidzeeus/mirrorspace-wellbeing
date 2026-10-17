/**
 * Sushi's face, the app's mascot and logo: a black cat in an orange beanie and round
 * white glasses, after the owner's reference drawing. Plain SVG with CSS animation
 * (globals.css, "Cat face"). Nothing is downloaded, and reduced motion stops all
 * movement (the expression itself still shows).
 *
 * - `expression`: how the face looks (happy, curious, sad, upset, calm, shy, surprised).
 * - `talking`: the mouth moves while a reply is read aloud.
 * - `thinking`: the head tilts while a reply is on its way.
 * - `breathing`: a slow grow-and-settle, to breathe along with.
 * - `hop`: a small happy bounce.
 */
export type Expression = "neutral" | "happy" | "curious" | "sad" | "upset" | "calm" | "shy" | "surprised";

export type CatFaceProps = {
  /** What the picture shows, for screen readers. Leave out when it is decoration. */
  label?: string;
  expression?: Expression;
  talking?: boolean;
  thinking?: boolean;
  breathing?: boolean;
  hop?: boolean;
  className?: string;
};

const ORANGE = "#ef5b25";
const ORANGE_DARK = "#c94416";
const BEIGE = "#ecdcc6";
const WHITE = "#ffffff";
const PINK = "#f4a6b8";

function Eyes({ expression }: { expression: Expression }) {
  switch (expression) {
    case "happy":
      // Smiling eyes: upturned arcs.
      return (
        <g fill="none" stroke={WHITE} strokeWidth="2.4" strokeLinecap="round">
          <path d="M42 69 Q 46 63 50 69" />
          <path d="M70 69 Q 74 63 78 69" />
        </g>
      );
    case "calm":
    case "shy":
      // Gently closed.
      return (
        <g fill="none" stroke={WHITE} strokeWidth="2.4" strokeLinecap="round">
          <path d="M42 66 Q 46 70 50 66" />
          <path d="M70 66 Q 74 70 78 66" />
        </g>
      );
    case "sad":
      return (
        <g className="cat-eyes" fill={WHITE}>
          <ellipse cx="46" cy="69" rx="2.6" ry="2.4" />
          <ellipse cx="74" cy="69" rx="2.6" ry="2.4" />
        </g>
      );
    case "surprised":
      return (
        <g fill={WHITE}>
          <circle cx="46" cy="66" r="4" />
          <circle cx="74" cy="66" r="4" />
        </g>
      );
    default:
      return (
        <g className="cat-eyes" fill={WHITE}>
          <ellipse cx="46" cy="67" rx="2.6" ry="3.2" />
          <ellipse cx="74" cy="67" rx="2.6" ry="3.2" />
        </g>
      );
  }
}

function Brows({ expression }: { expression: Expression }) {
  if (expression === "upset") {
    return (
      <g stroke={WHITE} strokeWidth="2.4" strokeLinecap="round">
        <path d="M38 52 L50 56" />
        <path d="M82 52 L70 56" />
      </g>
    );
  }
  if (expression === "sad") {
    return (
      <g stroke={WHITE} strokeWidth="2.2" strokeLinecap="round">
        <path d="M39 56 L50 52" />
        <path d="M81 56 L70 52" />
      </g>
    );
  }
  if (expression === "curious") {
    return (
      <g stroke={WHITE} strokeWidth="2.2" strokeLinecap="round">
        <path d="M70 51 Q 76 48 82 51" />
      </g>
    );
  }
  return null;
}

function Mouth({ expression }: { expression: Expression }) {
  const stroke = { fill: "none", stroke: WHITE, strokeWidth: 1.8, strokeLinecap: "round" as const };
  switch (expression) {
    case "happy":
      return <path d="M52 85 Q 60 93 68 85" {...stroke} strokeWidth={2} />;
    case "sad":
      return <path d="M54 89 Q 60 84 66 89" {...stroke} />;
    case "upset":
      return <path d="M54 88 Q 57 85 60 88 Q 63 85 66 88" {...stroke} />;
    case "surprised":
      return <ellipse cx="60" cy="88" rx="3.2" ry="3.8" fill="#7a1f33" stroke={WHITE} strokeWidth="1.5" />;
    default:
      return (
        <g {...stroke}>
          <path d="M60 83 Q 57 87.5 53.5 85" />
          <path d="M60 83 Q 63 87.5 66.5 85" />
        </g>
      );
  }
}

export function CatFace({
  label,
  expression = "neutral",
  talking = false,
  thinking = false,
  breathing = false,
  hop = false,
  className = "",
}: CatFaceProps) {
  const states = [
    talking && "is-talking",
    thinking && "is-thinking",
    breathing && "is-breathing",
    hop && "is-hopping",
    expression === "curious" && "is-curious",
    expression === "sad" && "is-sad",
    expression === "upset" && "is-upset",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div
      {...(label ? { role: "img", "aria-label": label } : { "aria-hidden": true })}
      data-cat-face
      data-expression={expression}
      data-talking={talking || undefined}
      className={`cat-face relative aspect-square ${states} ${className}`}
    >
      <svg viewBox="0 0 120 120" className="h-full w-full overflow-visible" aria-hidden="true">
        <circle cx="60" cy="62" r="56" fill={BEIGE} />
        <g className="cat-body">
          <g className="cat-head">
            {/* Ears, mostly under the hat. */}
            <path d="M24 48 L22 26 L40 38 Z" fill="#111111" />
            <path d="M96 48 L98 26 L80 38 Z" fill="#111111" />
            {/* Head. */}
            <path
              d="M60 32 C 86 32 98 50 98 70 C 98 92 82 104 60 104 C 38 104 22 92 22 70 C 22 50 34 32 60 32 Z"
              fill="#111111"
            />
            {/* Beanie: crown, ribbed band, pompom. */}
            <path d="M26 42 C 28 18 46 8 62 8 C 80 8 94 20 96 42 Z" fill={ORANGE} />
            <rect x="22" y="36" width="78" height="15" rx="7.5" fill={ORANGE} stroke={ORANGE_DARK} strokeWidth="1.2" />
            <g stroke={WHITE} strokeWidth="1.6" strokeLinecap="round" opacity="0.9">
              {[32, 39, 46, 53, 60, 67, 74, 81, 88].map((x) => (
                <path key={x} d={`M${x} 40 L${x} 47`} />
              ))}
            </g>
            <g className="cat-pompom">
              <circle cx="66" cy="7" r="8.5" fill={ORANGE} />
              <path
                d="M60 4 l3 2 M65 1 l1 3 M71 3 l-2 2 M62 10 l3 -1 M69 10 l-2 -2"
                stroke={ORANGE_DARK}
                strokeWidth="1.3"
                strokeLinecap="round"
              />
            </g>
            <Brows expression={expression} />
            {/* Round white glasses, with eyes behind them. */}
            <g fill="none" stroke={WHITE} strokeWidth="3.2">
              <circle cx="46" cy="66" r="10.5" />
              <circle cx="74" cy="66" r="10.5" />
              <path d="M56.5 65 Q 60 62.5 63.5 65" strokeWidth="2.6" />
            </g>
            <Eyes expression={expression} />
            {expression === "happy" || expression === "shy" ? (
              <g fill="#f472b6" opacity="0.55">
                <ellipse cx="33" cy="80" rx="5" ry="3" />
                <ellipse cx="87" cy="80" rx="5" ry="3" />
              </g>
            ) : null}
            {expression === "sad" ? (
              <path d="M50 76 q -2 4 0 6 q 2 -2 0 -6 Z" fill="#93c5fd" className="cat-tear" />
            ) : null}
            {/* Nose and mouth. */}
            <path d="M57.5 80 L62.5 80 L60 83 Z" fill={PINK} />
            <g className="cat-mouth-closed">
              <Mouth expression={expression} />
            </g>
            <g className="cat-mouth-open">
              <ellipse cx="60" cy="88" rx="5" ry="4.2" fill="#7a1f33" stroke={WHITE} strokeWidth="1.6" />
              <ellipse cx="60" cy="90.2" rx="2.8" ry="1.6" fill={PINK} />
            </g>
            {/* Whisker marks, white like the line details in the drawing. */}
            <g stroke={WHITE} strokeWidth="1.4" strokeLinecap="round" opacity="0.85">
              <path d="M30 82 L40 83" />
              <path d="M31 88 L40 86.5" />
              <path d="M90 82 L80 83" />
              <path d="M89 88 L80 86.5" />
            </g>
          </g>
          {/* Shy: paws come up over the glasses. */}
          {expression === "shy" ? (
            <g className="cat-paws">
              <g fill="#3a3a44" stroke={WHITE} strokeWidth="1.6">
                <ellipse cx="45" cy="68" rx="13" ry="10.5" />
                <ellipse cx="75" cy="68" rx="13" ry="10.5" />
              </g>
              <g fill={PINK}>
                <ellipse cx="45" cy="71" rx="4.5" ry="3.4" />
                <circle cx="39" cy="64" r="2" />
                <circle cx="45" cy="62" r="2" />
                <circle cx="51" cy="64" r="2" />
                <ellipse cx="75" cy="71" rx="4.5" ry="3.4" />
                <circle cx="69" cy="64" r="2" />
                <circle cx="75" cy="62" r="2" />
                <circle cx="81" cy="64" r="2" />
              </g>
            </g>
          ) : null}
        </g>
      </svg>
    </div>
  );
}
