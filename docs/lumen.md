# The Lumen

The Lumen is the app's one glowing object: a cluster of small dots that gathers, brightens, breathes and rests. It lives in `frontend/src/components/lumen/` and nowhere else draws particles.

## The rule

It is never decoration. Every use passes a `label` that says, in words, what the light is showing, and its props map to something real.

| Where | What it shows | Props that change |
|---|---|---|
| Landing hero | The app arriving | `assemble` (gathers once on load) |
| Landing story | The three-part promise | `mode`: `orb`, then `figure`, then `pair` |
| Check-in | The mood answer, as it moves | `intensity`, `density`, `hue` |
| Breathing | The breath | `breathPhase` (0 fully out, 1 fully in) |
| Home | Which of the last seven days have a check-in | `mode="week"`, `lit` |

The week view lights a cluster for each day that has a check-in. It says nothing about how those days went, and the text next to it says so.

## Props

| Prop | Type | Meaning |
|---|---|---|
| `label` | string, required | Text alternative. Read by screen readers; the element has `role="img"`. |
| `mode` | `orb` \| `figure` \| `pair` \| `week` | The shape the dots take. |
| `intensity` | 0 to 1 | Brightness. |
| `density` | 0 to 1 | Share of the dots shown. |
| `hue` | 0 to 1 | 0 is cool violet, 1 is soft teal. No red: nothing here signals "bad". |
| `breathPhase` | 0 to 1, or undefined | Scales the shape between 72% and 100%. |
| `lit` | boolean[7] | For `week`: which days are lit. |
| `assemble` | boolean | Start scattered and gather. Used once, on the landing page. |

## Files

| File | What it does |
|---|---|
| `shapes.ts` | Generates the target points for each mode from code, with a seeded random source. No image assets. The same code runs on the server and in the browser, so both produce identical dots. |
| `Lumen.tsx` | The component: the static SVG, the animation loop, both renderers, and the frame-rate guard. |

## Rendering chain

1. **Static SVG (always).** The server renders about 260 dots as an inline SVG. This is what appears first, what is shown with JavaScript off, and what reduced-motion and low-bandwidth users keep.
2. **WebGL points.** When animation is allowed, a canvas takes over and the SVG is hidden. Up to 840 dots are drawn as round points by a small shader.
3. **Canvas 2D.** If the browser has no WebGL, the same dots are drawn with the 2D canvas, batched into four paths (one per brightness level).

The element carries `data-renderer` (`static`, `webgl` or `canvas2d`) so tests and debugging can see which one is active.

## When it does not animate

| Condition | Result |
|---|---|
| The system "reduce motion" setting, or the in-app toggle | Static SVG. On the breathing screen a progress ring and words replace it. |
| Low-bandwidth mode, or a slow or data-saving connection | Static SVG. No canvas is ever created. |
| JavaScript off | Static SVG. |
| Off screen, or the tab is hidden | The loop pauses. |
| Below 50 frames a second | See below. |

## Frame-rate guard

After a 30-frame warm-up the component measures 90 frames at a time. If the rate is under 50 a second it halves the particle count (down to a floor of 210). If it is still under 50 at the floor, it stops animating and shows the static SVG for the rest of the visit. It never stutters along.

## Halftone look

Each dot's brightness is snapped to one of four levels with a small fixed offset per dot, and brighter dots are drawn larger. That quantisation is what gives the dither or dot-matrix feel, rather than a smooth glow.

## Testing

`frontend/e2e/landing.spec.ts` checks that reduced motion, the in-app toggle and low-bandwidth mode all leave zero canvases, that the page works with JavaScript off, and that the Lumen always has its text alternative. `frontend/e2e/wellbeing.spec.ts` checks that the label follows the mood slider.
