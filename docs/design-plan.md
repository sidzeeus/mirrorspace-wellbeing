# Frontend design plan

Written before any frontend code (README Prompt 4), checked against README Part C and against generic defaults, then revised. The revisions are listed at the end.

## Concept

"Night Light": a calm dark room where the one thing that glows is the thing that matters. Light is the language. It gathers when you arrive, answers when you check in, breathes with you, and rests when you rest. Everything that is not light stays quiet: hairlines, plain type, generous space.

## Tokens

Colors are roles, defined once as CSS variables and swapped per theme. Tailwind reads the variables, so no component names a hex value.

| Role | Night (default) | Daybreak | Used for |
|---|---|---|---|
| `ink` | `#06070C` | `#F5F6FB` | Page background |
| `surface` | `#0E1018` | `#FFFFFF` | Panels |
| `surface-raised` | `#161926` | `#ECEEF7` | Dialogs, popovers |
| `line` | moon at 12% | ink-text at 14% | Hairlines |
| `moon` | `#EDEBFF` | `#14152A` | Primary text |
| `moon-dim` | `#9B9AB8` | `#55577A` | Secondary text |
| `lumen` | `#7C74F2` | `#4A41C9` | Accent: links, focus, the glow |
| `lumen-hi` | `#B9B4FF` | `#2B2670` | Primary button fill, highlights |
| `calm` | `#7FD6C2` | `#0F6F60` | Saved, completed |
| `warm` | `#F2C078` | `#8A5A00` | Gentle attention, "unreviewed" labels |
| `care` | `#F29BA8` | `#A8324A` | Support (SOS) only |

Contrast is checked in the Playwright suite with axe on every screen in both themes.

## Type

| Step | Size / line | Weight | Face | Use |
|---|---|---|---|---|
| display | clamp(2.5rem, 7vw, 5rem) / 1.02 | 300 | Hanken Grotesk | Landing headline only |
| h1 | clamp(1.9rem, 4vw, 2.75rem) / 1.1 | 300 | Hanken Grotesk | One per screen |
| h2 | 1.375rem / 1.25 | 400 | Hanken Grotesk | Section headings |
| body | 1rem / 1.6 | 400 | Hanken Grotesk | Text, max 68 characters wide |
| small | 0.875rem / 1.5 | 400 | Hanken Grotesk | Help text |
| data | 0.875rem / 1.4 | 400 | IBM Plex Mono | Dates, counts, timers, versions |

Sentence case everywhere. No all-caps labels. Headlines are set in two tones (moon, then moon-dim) to give long statements rhythm. Devanagari uses Noto Sans Devanagari with line-height 1.8. "Larger text" raises the root size to 112.5%.

## Shape and depth

- Structural panels: square corners, 1px hairline. Corner crop marks only on three stages: the landing hero, the Lumen stage, the Support panel.
- Controls (inputs, choice chips, list rows): 14px radius.
- Primary buttons and the Lumen: fully round.
- Depth is light, not shadow: a soft radial glow behind the Lumen and translucent glass for the navigation bars (solid fallback where `backdrop-filter` is missing).

## Motion

One orchestrated moment per page; everything else is still.

| Screen | The moment |
|---|---|
| Landing | The Lumen gathers from scattered points, once. On scroll it becomes a figure, then two figures reaching. |
| Check-in | The Lumen answers the mood slider as it moves. |
| Breathing | The Lumen expands and contracts on the chosen pace. |
| Home | The week settles into seven clusters. |
| Support | None. |

Page changes are a 220ms cross-fade. Reduced motion (system setting or the in-app toggle) replaces every animation with a static state. Low-bandwidth mode never starts a canvas and drops the web fonts.

## Layout: landing

```text
mobile                              desktop (>= 1024)
+----------------------------+      +-----------------------------------------------+
| name            Sign in    |      | name                         Helplines Sign in|
|                            |      |                                               |
|   + - - - - - - - - - +    |      |  Notice your patterns.      + - - - - - - - + |
|   |      . : ' : .    |    |      |  Find one small step.       |   . : ' : .   | |
|   |    : (lumen)  :   |    |      |  Reach real help            |  : (lumen) :  | |
|   + - - - - - - - - - +    |      |  when you need it.          |   ' : . : '   | |
|                            |      |                             + - - - - - - - + |
| Notice your patterns.      |      |  [Create an account]  See helplines           |
| Find one small step.       |      |  Not therapy. Not an emergency service.       |
| Reach real help when...    |      +-----------------------------------------------+
| [Create an account]        |      | sticky lumen stage  |  1  Notice              |
| See helplines              |      | (one light ->       |  2  One small step      |
+----------------------------+      |  figure -> two)     |  3  Real help           |
| story: 3 steps, stage on   |      +-----------------------------------------------+
| top, text below            |      | What this is        | What this is not        |
+----------------------------+      | (two ruled columns, not cards)                |
| is / is not (stacked)      |      +-----------------------------------------------+
| helplines strip            |      | helplines strip (number, region, verified on) |
| footer statement           |      | footer: two-tone statement, links             |
+----------------------------+      +-----------------------------------------------+
```

## Layout: app shell

```text
mobile                              desktop (>= 1024)
+----------------------------+      +------+--------------------------------+----------+
| screen title      Support  |      | name |                                | today    |
|                            |      |      |   + - - - - - - - - - - - +    | one      |
|   one idea per screen      |      | Home |   |                       |    | small    |
|                            |      | Check|   |     central stage     |    | step     |
|                            |      | Exer |   |                       |    |          |
|                            |      | Plan |   + - - - - - - - - - - - +    | quick    |
|                            |      | More |                                | links    |
+----------------------------+      |      |                                |          |
| Home Check Exer Plan More  |      |[Supp]|                                |          |
+----------------------------+      +------+--------------------------------+----------+
```

Support is a real link to `/support` on every screen (top right on mobile, bottom of the rail on desktop), in the `care` color, never inside a menu. Because it is a link and not a script-driven dialog, it works offline and before JavaScript loads.

## Self-review against generic defaults, and what changed

| Generic default I had drifted into | Why it is wrong here | Revision |
|---|---|---|
| A purple gradient button on black as the only accent | That is the single-bright-accent-on-black look, and a glowing purple button competes with the Lumen. | The Lumen is the only thing that glows. Primary buttons are a flat pale fill (`lumen-hi`) with dark text. Support has its own color (`care`), used nowhere else. |
| Three identical rounded cards for "Notice / Step / Help" | Identical cards are the template look, and they made the promise read like a feature list. | The promise is a scroll story: numbered text beside a sticky stage in which the Lumen changes form. No cards. |
| "What it is / is not" as two cards with icons | Same card repetition; icons add nothing. | Two ruled columns of plain sentences, like a printed notice. |
| An all-caps eyebrow above every heading | README C.3 forbids all-caps labels and stacked eyebrows. | Removed. Where a section needs a marker it is a mono numeral (1, 2, 3). |
| Fade-and-slide-up on every section as it scrolls in | Scattered effects; README C.4 allows one moment per page. | Only the Lumen moves. Sections are simply there. |
| One 16px radius on everything | README C.3 asks for radii by hierarchy. | Square structural panels, 14px controls, round buttons. |
| Centered hero with the orb as a background decoration | The Lumen must never be decoration. | The hero Lumen sits in a framed stage with crop marks and is the same object that later reflects the check-in. Its text alternative says what it is. |
| A streak counter and "great job" on the dashboard | README C.4: no streaks, no praise, no guilt. | The week view shows which days have a check-in as lit clusters, with one neutral sentence. |
| Framer Motion for transitions | It would add about 40 KB to every page for effects CSS can do, against the performance budget. | CSS transitions only. Recorded as a decision. |
| Theme, text size and motion saved to the account | Those are device comforts, not account data. | Kept in the browser only. Language is the one preference stored on the account. |

## Components

Button, IconButton, Panel (hairline, optional crop marks), GlassPanel, Field and Input, Slider, Toggle, Dialog, Toast, Tabs, ProgressRing, VisuallyHidden, SkipLink, ScaleControl (the 1 to 5 choice used for sleep quality, energy, stress and intensity), and the Lumen. Interactive primitives come from Radix so focus handling and ARIA are correct. Touch targets are at least 44px.

## The Lumen

One isolated component, documented in `docs/lumen.md`.

- Props: `mode` (orb, figure, pair, week), `intensity`, `density`, `hue`, `breathPhase`, `lit`.
- It always has a text alternative that states what it is showing.
- Rendering chain: a static SVG of dots is rendered on the server, so there is always an image, including with JavaScript off. In the browser it upgrades to WebGL, or to Canvas 2D if WebGL is unavailable. Reduced motion and low-bandwidth mode keep the static SVG.
- It measures its own frame rate. Below 50 frames a second it halves its particle count; if that is not enough it stops animating and shows the static image.
