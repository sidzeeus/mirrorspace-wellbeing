/**
 * Sushi in full: a black cat sitting with a ball of orange yarn and two knitting
 * needles, wearing the orange beanie and round white glasses, after the owner's
 * reference drawing. Plain SVG; the movement is CSS (globals.css, "Sushi character"):
 * Sushi blinks, sways its tail, knits, and bobs its head a little. Reduced motion
 * stops all of it.
 */
const ORANGE = "#ef5b25";
const ORANGE_DARK = "#b9400f";
const BLACK = "#111111";
const WHITE = "#ffffff";
const BEIGE = "#ecdcc6";

export function SushiCharacter({ label, className = "" }: { label?: string; className?: string }) {
  return (
    <div
      {...(label ? { role: "img", "aria-label": label } : { "aria-hidden": true })}
      data-sushi-character
      className={`sushi relative ${className}`}
    >
      <svg viewBox="0 0 220 230" className="h-full w-full overflow-visible" aria-hidden="true">
        {/* A soft backdrop, the beige of the reference, so a black cat reads on a dark sky. */}
        <ellipse cx="112" cy="132" rx="104" ry="96" fill={BEIGE} />

        {/* Tail, curling up behind on the right. */}
        <g className="sushi-tail">
          <path
            d="M160 196 C 196 192 206 160 196 128 C 190 108 198 92 206 98"
            fill="none"
            stroke={BLACK}
            strokeWidth="13"
            strokeLinecap="round"
          />
        </g>

        {/* Body, sitting. */}
        <path
          d="M78 118 C 56 140 50 184 66 208 C 74 220 150 222 164 208 C 182 186 172 140 150 118 Z"
          fill={BLACK}
        />
        {/* White line details, like the drawing: belly and back leg. */}
        <g fill="none" stroke={WHITE} strokeWidth="2.4" strokeLinecap="round">
          <path d="M150 140 C 160 160 160 182 150 198" />
          <path d="M132 206 C 146 206 156 200 160 192" />
        </g>
        {/* Back foot peeking out. */}
        <ellipse cx="66" cy="212" rx="16" ry="8" fill={BLACK} stroke={WHITE} strokeWidth="2" />

        {/* The ball of yarn, held in front. */}
        <g className="sushi-yarn">
          <circle cx="98" cy="176" r="36" fill={ORANGE} />
          <g fill="none" stroke={ORANGE_DARK} strokeWidth="2.6" strokeLinecap="round">
            <path d="M66 166 C 84 150 116 148 132 160" />
            <path d="M64 180 C 86 164 120 164 134 176" />
            <path d="M70 196 C 90 180 118 182 128 194" />
            <path d="M80 146 C 74 168 80 196 96 210" />
            <path d="M100 141 C 92 164 98 192 114 208" />
            <path d="M120 148 C 112 168 116 190 128 200" />
          </g>
          {/* A loose strand of yarn trailing off. */}
          <path d="M126 200 C 140 214 128 222 146 224" fill="none" stroke={ORANGE} strokeWidth="2.4" strokeLinecap="round" />
        </g>

        {/* Knitting needles, crossing up and to the left. */}
        <g className="sushi-needles" stroke={BLACK} strokeWidth="3.2" strokeLinecap="round">
          <path d="M104 150 L 54 98" />
          <path d="M114 152 L 98 96" />
          <circle cx="52" cy="96" r="5" fill={WHITE} strokeWidth="2.4" />
          <circle cx="97" cy="93" r="5" fill={WHITE} strokeWidth="2.4" />
        </g>

        {/* Paws holding the yarn and needles. */}
        <g fill={BLACK} stroke={WHITE} strokeWidth="2">
          <ellipse cx="84" cy="150" rx="13" ry="10" transform="rotate(-25 84 150)" />
          <ellipse cx="124" cy="156" rx="13" ry="10" transform="rotate(20 124 156)" />
        </g>

        {/* Head: tilts a little now and then. */}
        <g className="sushi-head">
          <path d="M62 64 L 58 34 L 84 50 Z" fill={BLACK} />
          <path d="M162 64 L 166 34 L 140 50 Z" fill={BLACK} />
          <path
            d="M112 44 C 146 44 162 66 162 90 C 162 116 140 130 112 130 C 84 130 62 116 62 90 C 62 66 78 44 112 44 Z"
            fill={BLACK}
          />
          {/* Beanie. */}
          <path d="M66 58 C 68 26 92 12 112 12 C 136 12 156 26 158 58 Z" fill={ORANGE} />
          <rect x="60" y="50" width="104" height="19" rx="9.5" fill={ORANGE} stroke={ORANGE_DARK} strokeWidth="1.4" />
          <g stroke={WHITE} strokeWidth="2" strokeLinecap="round" opacity="0.9">
            {[72, 81, 90, 99, 108, 117, 126, 135, 144, 153].map((x) => (
              <path key={x} d={`M${x} 55 L${x} 64`} />
            ))}
          </g>
          <g className="sushi-pompom">
            <circle cx="118" cy="10" r="11" fill={ORANGE} />
            <path
              d="M110 6 l4 3 M117 2 l1 4 M125 4 l-3 3 M113 14 l4 -1 M122 14 l-2 -3"
              stroke={ORANGE_DARK}
              strokeWidth="1.6"
              strokeLinecap="round"
            />
          </g>
          {/* Round white glasses, eyes behind them. */}
          <g fill="none" stroke={WHITE} strokeWidth="4">
            <circle cx="95" cy="88" r="13.5" />
            <circle cx="129" cy="88" r="13.5" />
            <path d="M108.5 87 Q 112 84 115.5 87" strokeWidth="3" />
          </g>
          <g className="sushi-eyes" fill={WHITE}>
            <ellipse cx="95" cy="89" rx="3.2" ry="4" />
            <ellipse cx="129" cy="89" rx="3.2" ry="4" />
          </g>
          <path d="M109 104 L 115 104 L 112 108 Z" fill="#f4a6b8" />
          <g fill="none" stroke={WHITE} strokeWidth="2" strokeLinecap="round">
            <path d="M112 108 Q 108 113 104 110" />
            <path d="M112 108 Q 116 113 120 110" />
          </g>
          <g stroke={WHITE} strokeWidth="1.6" strokeLinecap="round" opacity="0.85">
            <path d="M70 104 L 82 105" />
            <path d="M71 111 L 82 109" />
            <path d="M154 104 L 142 105" />
            <path d="M153 111 L 142 109" />
          </g>
        </g>
      </svg>
    </div>
  );
}
