/**
 * Sushi's face: a black cat in an orange beanie and round white glasses, after the
 * owner's reference drawing. Plain SVG with CSS animation (globals.css, "Cat face"):
 * it blinks now and then, its mouth moves while a reply is spoken aloud (`talking`), and
 * it tilts its head while a reply is on its way (`thinking`). Reduced motion stops all
 * of it. Nothing is downloaded.
 */
export type CatFaceProps = {
  /** What the picture shows, for screen readers. Leave out when it is decoration. */
  label?: string;
  /** The mouth moves, as if speaking. */
  talking?: boolean;
  /** The head tilts while waiting for a reply. */
  thinking?: boolean;
  className?: string;
};

const ORANGE = "#ef5b25";
const ORANGE_DARK = "#c94416";
const BEIGE = "#ecdcc6";

export function CatFace({ label, talking = false, thinking = false, className = "" }: CatFaceProps) {
  return (
    <div
      {...(label ? { role: "img", "aria-label": label } : { "aria-hidden": true })}
      data-cat-face
      data-talking={talking || undefined}
      className={`cat-face relative aspect-square ${talking ? "is-talking" : ""} ${
        thinking ? "is-thinking" : ""
      } ${className}`}
    >
      <svg viewBox="0 0 120 120" className="h-full w-full overflow-visible" aria-hidden="true">
        <circle cx="60" cy="62" r="56" fill={BEIGE} />
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
          <g stroke="#ffffff" strokeWidth="1.6" strokeLinecap="round" opacity="0.9">
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
          {/* Round white glasses, with eyes that blink behind them. */}
          <g fill="none" stroke="#ffffff" strokeWidth="3.2">
            <circle cx="46" cy="66" r="10.5" />
            <circle cx="74" cy="66" r="10.5" />
            <path d="M56.5 65 Q 60 62.5 63.5 65" strokeWidth="2.6" />
          </g>
          <g className="cat-eyes" fill="#ffffff">
            <ellipse cx="46" cy="67" rx="2.6" ry="3.2" />
            <ellipse cx="74" cy="67" rx="2.6" ry="3.2" />
          </g>
          {/* Nose and mouth. */}
          <path d="M57.5 80 L62.5 80 L60 83 Z" fill="#f4a6b8" />
          <g className="cat-mouth-closed" fill="none" stroke="#ffffff" strokeWidth="1.8" strokeLinecap="round">
            <path d="M60 83 Q 57 87.5 53.5 85" />
            <path d="M60 83 Q 63 87.5 66.5 85" />
          </g>
          <g className="cat-mouth-open">
            <ellipse cx="60" cy="88" rx="5" ry="4.2" fill="#7a1f33" stroke="#ffffff" strokeWidth="1.6" />
            <ellipse cx="60" cy="90.2" rx="2.8" ry="1.6" fill="#f4a6b8" />
          </g>
          {/* Whisker marks, white like the line details in the drawing. */}
          <g stroke="#ffffff" strokeWidth="1.4" strokeLinecap="round" opacity="0.85">
            <path d="M30 82 L40 83" />
            <path d="M31 88 L40 86.5" />
            <path d="M90 82 L80 83" />
            <path d="M89 88 L80 86.5" />
          </g>
        </g>
      </svg>
    </div>
  );
}
