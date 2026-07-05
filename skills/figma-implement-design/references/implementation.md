# Implementation playbook

How to turn the specs you extracted (SKILL.md §3) into code that matches the
design 1:1. Order: **project conventions first, Figma values where the project
has no token, exact numbers everywhere.**

## 1. Autolayout → CSS (the core mapping)

Figma autolayout is 1-dimensional, so it maps directly to **flexbox**. Read
these off the parent frame's inspect panel and translate:

| Figma inspect | CSS | Notes |
|---|---|---|
| `Flow: Horizontal` | `display:flex; flex-direction:row` | |
| `Flow: Vertical` | `display:flex; flex-direction:column` | |
| `Gap: N` | `gap: Npx` | spacing between children — **not** child margins |
| `Padding: T/R/B/L` | `padding: T R B L` | lives on the container |
| `Justify: space-between` | `justify-content: space-between` | also `center`, `flex-start`, `flex-end` |
| align (packed/center/…) | `align-items: …` | Figma's cross-axis alignment |
| `Wrap: yes` | `flex-wrap: wrap` | if present |
| `Radius: N` | `border-radius: Npx` | per-corner values map to the 4 corners |
| `Border: Npx <color>` | `border: Npx solid <color>` | check side-specific (e.g. `Bottom 0.5px`) → `border-bottom` |
| `Clip content` on | `overflow: hidden` | |

### Width / Height: Fixed / Fill / Hug
This is the sizing model — get it right or the layout won't flex correctly:

| Figma | Meaning | CSS |
|---|---|---|
| `Fixed (Npx)` | exact size | `width:Npx` / `height:Npx` |
| `Fill` | fill the parent's available space along the axis | `flex:1 1 0` (main axis) or `align-self:stretch` / `width:100%` (cross axis) |
| `Hug` | shrink to fit contents | `width:fit-content` / just let content size it |

`Fill` on the main axis = `flex:1`; on the cross axis = stretch/100%. `Hug` = the
default content size (don't set a width). Prefer these semantics over hardcoded
px so the component stays responsive — a `Fill` child should be `flex:1`, not the
literal `367.33px` the inspect shows at the current zoom.

## 2. Padding & margins stay sound (the one rule)

Figma has **no margins** — an autolayout frame owns its **padding** (all sides)
and the **gap** between children. Replicate exactly:

- Container: `padding` (from the frame) + `gap` (from the frame).
- Children: `margin: 0`. Spacing between them is the parent's `gap`, nothing else.

This eliminates margin-collapse guesswork and is why extracted spacing "just
works." If you find yourself adding a child margin to fix spacing, you've missed
the parent's gap/padding — go re-read the parent frame.

## 3. Flex vs. Grid — pick per design

- **Flex (default):** anything autolayout — rows, columns, toolbars, cards,
  stacks. One direction, optionally wrapping.
- **CSS Grid:** use only for a **true 2-D grid** — a gallery of cards that
  wraps into N columns, a dashboard with row+column tracks, an N-column form.
  Signals: the design repeats a cell on both axes, or "auto-fill/auto-fit"
  reflow is desired. Then `grid-template-columns: repeat(auto-fill, minmax(…))`
  with the frame's `gap`.

Match the project: if it uses a grid/spacing system (Tailwind, a `<Stack>`/`<Grid>`
primitive, CSS vars), express the mapping in that system rather than raw CSS.

## 4. Component decomposition (React source of truth)

The Layers tree (SKILL.md §2) is the decomposition. Method:

1. **Each named autolayout frame → one component** (e.g. a `Header`, `Sidebar`,
   or `Card` frame).
2. **Repeated siblings → a list.** N identical sibling frames → one component
   `<Card {...data}/>` mapped over an array. The differing text/number/icon are
   the props.
3. **Figma Component properties → React props.** A variant prop like `Number of
   Tabs: 1`, `Notification: No`, `Icons: true`, `Tab 1: Overview` is literally
   the prop surface. Booleans → boolean props; instance-swaps → children/slots;
   text props → string props.
4. **Modes / variables → theme.** Light/dark or brand **Modes** map to your
   theme/`:root` variables; the color **token names** (`Gray/Gray 900`) are the
   variable names.
5. **Ownership split:** the **parent** owns layout, flow, gap, and outer padding;
   each **child** owns its own content and inner padding. Don't leak a child's
   spacing into the parent or vice-versa.

Keep the prop surface as small as the design's actual variants. Don't invent
configurability the design doesn't show (user: "don't overcomplicate").

## 5. Typography & fonts (exact)

Use the extracted values verbatim — no rounding:

```css
/* from inspect: Inter Tight / 500 / 20px / 130% / -1% / "Heading 3 Medium" */
font-family: 'Inter Tight', sans-serif;
font-weight: 500;
font-size: 20px;
line-height: 1.3;        /* 130% */
letter-spacing: -0.01em; /* -1% → em, or -0.2px at 20px */
```

- **Line height %** → unitless ratio (`130%` → `1.3`) or px.
- **Letter spacing %** → `em` (`-1%` → `-0.01em`), which scales with size.
- **Reuse the text-style name** (`Heading 3 Medium`) as your typography token if
  the project has a type scale; else define it once and reuse.
- **Load the font for real.** If it's a Google/web font (Inter Tight, Poppins,
  etc.), wire it through the project's existing font setup (Next `next/font`, a
  `<link>`, `@font-face`, Tailwind `fontFamily`). Naming a family that isn't
  loaded silently falls back and breaks fidelity. Match the **exact weights** you
  use (400/500/600…) — load only those.

## 6. Colors

- Prefer the **token name** (`Gray/Gray 900`, `Primary/500`) mapped to the
  project's variable/theme.
- Else use the **hex** from inspect. Switch the inspect "Color format" dropdown to
  `CSS`/`RGB` if you need alpha or a copy-paste value.
- Gradients and multiple fills show as stacked entries — reproduce the order
  (top fill = last painted).

## 7. Effects (shadows, blur)

The inspect **Effects** section lists drop/inner shadows and blurs with x/y/blur/
spread/color. Map to `box-shadow` / `filter: blur()`. Read them; don't eyeball a
shadow.

## 8. Icons — the exact Figma vector, not a name-match

**The layer name identifies the icon** — Figma icon layers are usually named
`<category>/<solid|line>/<name>` (e.g. `navigation/solid/home`), giving the glyph
and the solid/line variant. But **a same-named icon already in the project is
often a different drawing**, so reusing project icons by name alone can leave the
UI visibly off. For fidelity, get the **actual Figma vector**: select the icon →
inspect **Export** → SVG → *Export*,
then `Read` the file and inline it. Reuse an existing project icon **only after a
visual diff** at high zoom (glyph, weight, solid/line identical). Read the icon's
color (active vs. inactive) and size from inspect. Note solid vs. line — many icon
systems store them as separate files or a `type` prop (solid=fill, line=stroke).

**Watch the path `fill` — this is a recurring, invisible-in-Figma bug.** A repo's
icon component often injects `fill`/`stroke` onto the root `<svg>` and expects
paths to carry a `fill=""` placeholder (or no fill) so the injected color
**inherits** down. **A path with its own `fill` — `"none"`, `"white"`, or a hex —
overrides that injection**, so the icon renders invisible/white or an evenodd
cut-out fills in — e.g. a path that ships with `fill="none"` or a baked-in
`fill="white"` looks fine in Figma but renders wrong in the app. Fix: normalize
the path fill to the project's convention (or re-export from Figma), and **verify
each icon in the running app** — `getComputedStyle(svgPath).fill` plus a zoomed
screenshot — not just in Figma. When authoring, open an existing icon file and
mirror its `viewBox` and fill/stroke structure.

### Reusable wrapper (when the project has none)

Ship icons inline. A tiny wrapper keeps them consistent and colorable:

```tsx
type IconProps = { size?: number; className?: string };
export const ChevronDown = ({ size = 20, className }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
       stroke="currentColor" strokeWidth={2} strokeLinecap="round"
       strokeLinejoin="round" className={className}>
    <path d="m6 9 6 6 6-6" />
  </svg>
);
```

- `stroke="currentColor"` so the icon inherits text color (match the icon's
  inspect fill/stroke token).
- Pull `viewBox`, stroke-width, and fill-vs-stroke from the icon's inspect panel;
  confirm the exact path by zooming in (`Shift+2`) and screenshotting.
- Most UI icons are standard (Feather/Lucide-style, 24×24, 2px stroke) — author
  from the screenshot rather than importing a package. Only custom/brand marks
  need an Export-SVG round-trip (SKILL.md §5).

## 9. Framework notes

- **React** (assumed source of truth): components per §4; co-locate styles the
  way the project does (CSS Modules, Tailwind, styled-components, vanilla-extract).
- **Tailwind:** map spacing to the scale but use **arbitrary values** (`gap-[24px]`,
  `rounded-[24px]`, `text-[20px]`) when the design value isn't on the scale — don't
  snap to the nearest token and lose fidelity.
- **Plain CSS / other frameworks:** same mapping; put the numbers in variables
  named after the Figma tokens.
- **Reuse first:** if the project already has a `Card`, `Button`, `Badge`, or type
  token that matches, use it instead of duplicating. Extend it only if the design
  genuinely differs.

## 10. Fidelity-diff checklist

Before calling it done, verify your render against the Figma spec — read
`getComputedStyle` on the running app (exact) and compare per-element at high zoom
(SKILL.md §7) — against this list:

- [ ] **Layout:** flow direction, gap, padding (all sides), justify/align, wrap.
- [ ] **Sizing:** Fill/Hug/Fixed behavior correct (does it flex/shrink right?).
- [ ] **Typography:** family, weight, size, line-height, letter-spacing, color,
      alignment, truncation. **Every type class you referenced actually exists**
      (`grep` it — a missing class like `heading-2-medium` fails silently).
- [ ] **Radius & borders:** per-corner radius, border width/side/color.
- [ ] **Colors & fills:** background, **every text label's color** (title AND
      value — not just the one you changed), borders, gradients, opacity.
- [ ] **Alignment:** each row's `justify-content` + `align-items`; badges/labels
      that must be right-aligned and vertically centered actually are.
- [ ] **Sub-components:** dropdowns/menus, count badges ("N new"), chips — match
      fill/border/radius/typography and the real count, not the project's version.
- [ ] **Icons:** the exact Figma vector (not a name-matched lookalike); size,
      color, solid/line variant, position — **and each actually renders in the
      app** (right color/cut-outs, not white/invisible; check `computedStyle.fill`).
- [ ] **Overrides applied:** styles passed into a shared component's `className`
      actually took effect (computed styles) — defaults/CSS-order didn't clobber them.
- [ ] **Effects:** shadows, blur.
- [ ] **States:** hover/focus/active/disabled/empty/loading (§edge cases).
- [ ] **Overflow:** long text/lists truncate or scroll, don't break layout.
- [ ] **Responsive:** matches Mobile frame if one exists; fluid otherwise.

Fix diffs, re-shoot, repeat. Note any intentional deviation and the reason.
