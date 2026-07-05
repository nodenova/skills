---
name: figma-implement-design
description: >-
  Read a Figma design with native browser automation (Claude-in-Chrome) and
  implement it as UI at 100% visual fidelity. Use when the user gives a
  figma.com/design link and wants a component/screen built in code. It stops an
  agent eyeballing pixels: the user's real
  Chrome is signed into Figma, so a file has TWO content types — the canvas art
  is WebGL pixels (screenshot it); the right-rail inspect panel exposes EXACT
  specs as DOM text (extract with javascript_tool, don't guess): font, size,
  line-height, radius, padding, gap, autolayout flow, fills. The
  left Layers panel is the component tree. First inventory the project's type
  scale/tokens/icons and verify a token exists before mapping a Figma value onto
  it. Loop: select a node on the canvas (double-click to drill in) and VERIFY its
  name (Layers-row clicks mis-hit), Shift+2 to zoom, screenshot, extract specs,
  build. Verify with getComputedStyle on the running app + high-zoom,
  adversarially — a full-page glance misses diffs (colors, alignment,
  sub-components, borders, icons that render white). Icons: export the exact SVG
  from Figma; a name-matched icon often differs, and a hardcoded path fill renders
  it white. Autolayout → flex/grid: container
  padding + gap, children have NO margins. Gotchas: Dev Mode may be locked but
  design-mode inspect suffices; javascript_tool BLOCKS reading location/cookies;
  clipboard read is denied. Triggers: "implement
  this figma", "build this design in
  react", "figma to code", "match this mockup".
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, mcp__claude-in-chrome
---

# Figma → UI (native browser automation)

Drive **Claude-in-Chrome live** to read a Figma design and build it in code at
**100% fidelity**. This is interactive: open the file once, then for each piece
you **select → frame → screenshot → extract specs → build → compare**. Keep the
session open (a Figma tab plus a tab on the running app). There is no one-shot
script that gathers a design — the specs come from selecting nodes and reading
the inspect panel.

If the Claude-in-Chrome tools aren't loaded yet, load them first (one batched
`ToolSearch`) — see the [claude-in-chrome guidance](#tooling). Prefer
`browser_batch` to run several actions in one round trip.

## Read this before you start (saves an hour of eyeballing pixels)

A Figma file, like a Miro board, has **two kinds of content, read differently:**

1. **Exact specs live in the DOM — read them, don't eyeball them.** The
   right-rail **Properties / inspect panel** shows the selected node's real
   values: font family, weight, size, line-height, letter-spacing,
   border-radius, per-side padding, gap, autolayout flow, fills (hex + token
   name), strokes, effects, and component/variant properties. Extract this with
   `javascript_tool` (§3). **The left Layers panel is the component tree** — your
   React structure. Both are DOM text.
2. **The rendered mockup is WebGL pixels — screenshot it** for visual truth
   (spacing rhythm, alignment, what an icon actually looks like, overlap/shadow).
   Never transcribe a number off a screenshot that the inspect panel can give
   you exactly.

**So: select a node, extract its specs as text, and screenshot it for the
look — never guess a value you can read.** A `20px`/`130%`/`-1%` you read off the
panel is right; the same value estimated from a screenshot is wrong.

Two facts that make the native browser the right tool here (vs. a headless one):

- **The user is already signed into Figma in their Chrome.** That's what unlocks
  the inspect panel and Layers tree on a shared file — no auth dance.
- **Keyboard shortcuts reach the canvas.** `Shift+2` (zoom to *selection*) frames
  the selected node perfectly before a screenshot — the big win over
  `agent-browser`, where they don't fire. (`Shift+1` fits *all* content on the
  page, which on a multi-frame file can be ~2% and useless — prefer `Shift+2`.)

Three constraints, learned the hard way — internalize them now:

- **`javascript_tool` blocks any code that touches `location`, `document.cookie`,
  or the query string** — it returns `[BLOCKED: Cookie/query string data]`. Never
  reference `location.href` etc. To read the current `node-id`, look at the **tab
  context** printed after each browser action, not JS.
- **Clipboard read is denied** (`navigator.clipboard.readText()` →
  `NotAllowedError`). "Copy as SVG" copies fine but you can't read it back
  programmatically — use the SVG paths in §5 instead.
- **Paid Dev Mode may be locked** ("Get coding, faster / Request access"). Don't
  wait on it — the ordinary **design-mode inspect panel is enough** for everything
  above.

## 0. Inventory the project's design system first (before Figma)

The task is usually "make the app follow Figma's design system" — so map every
Figma value onto the project's **existing** tokens; don't reinvent. Before
opening Figma, read the project's:

- **Fonts & type scale** — the CSS/Tailwind classes or tokens (e.g.
  `heading-2-medium`, `body-regular`) and how the fonts are loaded.
- **Color & spacing tokens**, the radius scale, shadow utilities.
- **Existing components** (Card, Button, Badge, Header, Sidebar) and the **icon
  set** (the SVG files / icon names available, and how the icon component colors
  them).

Then Figma's text-style names, color names, and icon layer-names map onto these
**by name**. **Critical: verify a token/class actually exists before you
reference it — `grep` it.** A Figma text style like "Heading 2 Medium" does *not*
guarantee a matching `.heading-2-medium` class exists — a scale often defines only
some weights (e.g. bold and regular but not medium). Referencing a class that
isn't there **fails silently**: the text loses its size/weight and nothing errors.
If the exact token is missing, **add it to the scale to match the Figma spec**
rather than pointing at a class that doesn't exist.

## 1. Open two tabs — the Figma file and the running app

Get the tab context, open Figma, wait for the WebGL canvas — Figma is a heavy SPA
and the tab title stays "New Tab" for a few seconds after `navigate`.

1. `tabs_context_mcp` (createIfEmpty: true) → get a `tabId`.
2. `navigate` to the **exact URL the user gave**, including `?node-id=<id>` — that
   param **selects and centers that node on load**, landing you on what they care
   about.
3. Wait ~4–5s, then confirm it rendered (cheap, before any screenshot):
   ```js
   JSON.stringify({canvas: document.querySelectorAll('canvas').length,
     title: document.title, view: document.body.innerText.includes('view and comment')})
   ```
   `canvas ≥ 1` and a real title mean it's up. Then screenshot once to orient.
4. **Open a second tab** (`tabs_create_mcp` → `navigate`) on the **running app**
   page you're matching (e.g. `http://localhost:3000/...`). Keep **both** tabs
   open — you'll flip between them to compare throughout (§7).

If the file shows a login / "Request access" wall, the user isn't signed in or
the link isn't shared to them — ask them to open it in their Chrome and sign in;
don't try to bypass an access wall. See [troubleshooting](references/troubleshooting.md).

## 2. Map the component tree (Layers panel = your structure)

Before extracting anything, read the **left Layers panel** — it *is* the
component decomposition, named by the designer. Read it as text:

```js
// Left rail (Pages + Layers). Climb from a known label to the tall left container.
(function(){let a=[...document.querySelectorAll('div,span')].find(e=>e.textContent.trim()==='Layers');
 let el=a; for(let i=0;i<12&&el.parentElement;i++){el=el.parentElement;
 const r=el.getBoundingClientRect(); if(r.left<300&&r.height>innerHeight*0.4)break;}
 return el.innerText.replace(/\n{2,}/g,'\n').trim();})()
```

The nesting (e.g. `PageContainer > CardRow > Card ×3 > …`) is your component
hierarchy, and the frame names are component-name candidates. Note which nodes
repeat (identical sibling frames → one component mapped over a data array). This
gives you a component-based structure: **each named autolayout frame is a
component; its repeated children are the props-driven list.**

**Select on the canvas, and verify the selection before extracting.** A **single
click selects the outermost frame** under the cursor; **double-click drills one
level deeper** each time (`Esc` steps back up). Clicking a **Layers row** also
selects, but **frequently mis-hits** — rows are tiny and the tree scrolls, so a
click often lands on a neighbor or does nothing. So after *any*
selection, **confirm the node name at the top of the inspect panel is the one you
meant** before trusting its specs — extracting from the wrong node (a header row
instead of the card, a text block instead of its frame) is the #1 time-sink. The
URL's `node-id` updates on every selection (visible in the tab context) — that's
your per-component deep link for the deliverable.

## 3. Extract exact specs (the inspect panel — do this, don't guess)

With a node selected, run this **class-name-independent** extractor (Figma's
hashed class suffixes change between builds, so anchor on visible section labels
and read `innerText`):

```js
// SELECTED-NODE SPECS. Do NOT touch location/cookies. Uses top-level structure only.
(function(){
  const labels=['Layout','Typography','Colors','Fill','Fills','Padding','Font','Stroke','Strokes','Effects'];
  let a=null;
  for(const el of document.querySelectorAll('div,span')){
    const own=[...el.childNodes].filter(c=>c.nodeType===3).map(c=>c.textContent.trim()).join('');
    if(labels.includes(own)){const r=el.getBoundingClientRect(); if(r.left>innerWidth*0.7){a=el;break;}}
  }
  if(!a) return 'NO PANEL — select a node first';
  let el=a;
  for(let i=0;i<15&&el.parentElement;i++){el=el.parentElement;
    const r=el.getBoundingClientRect(); if(r.left>innerWidth*0.7&&r.height>innerHeight*0.4)break;}
  return el.innerText.replace(/\n{2,}/g,'\n').trim();
})()
```

It returns name/value on alternating lines. What the fields mean and how they map
to CSS (full table in [implementation.md](references/implementation.md)):

- **Layout** → `Flow: Horizontal|Vertical` = `flex-direction: row|column`;
  `Width/Height: Fixed(px)|Fill|Hug` = fixed px / `flex:1` (or `width:100%`) /
  `fit-content`; `Justify` = `justify-content`, **`Align` = `align-items`
  (cross-axis) — reproduce BOTH**; `Gap` = `gap`; `Padding Top/Right/Bottom/Left`
  = `padding`. Wrong alignment (a badge that should be right-aligned / vertically
  centered but isn't) is a common miss — read `Align`/`Justify`, don't eyeball.
- **Radius** → `border-radius`. **Border** → width + color = `border`.
- **Typography** (text nodes) → `Font` (exact family, e.g. `Inter Tight`),
  `Weight` (numeric, e.g. `500`), `Size` (px), `Line height` (%), `Letter
  spacing` (%), plus the text-style `Name` (e.g. `Heading 3 Medium`) — match that
  name to the project's type class, **but verify the class exists** (§0) and add
  it if missing; never reference one that isn't there. `Content` = literal text.
- **Colors** → token name + hex (e.g. `Gray/Gray 900` `#353535`). The token name
  tells you which design-system variable to use; the hex is the fallback. A
  **Color format** dropdown in this section switches hex↔rgb↔css if you need it.
- **Component properties / Modes** → variant props (e.g. `Number of Tabs`,
  `Notification: No`, `Icons: true`) — these are literally your React props and
  the light/dark or theme **Modes** are your variables.

**Extract completely — every node, every property.** Parent frame first (padding
+ gap + flow + align), then **each child, including each text node's own color
AND alignment**, not just its size/weight. **Don't leave an element at its current
value because it "looks unchanged"** — e.g. a title left at the project's lighter
gray when the design specifies a darker one, because only the value's color was
read and the title's wasn't. Also extract the **sub-components** the design
contains — dropdowns/menus, badges and their **count text**, chips, avatars — each
has its own fill/border/radius/typography (and states); skip them and they stay
looking wrong. Read a node's specs **once**, but make sure you read *all* of them.

## 4. Capture the visual reference (fidelity anchor)

For each component and for the whole screen:

1. Select the node (canvas click/drill, §2) and verify its name.
2. **`Shift+2`** → zoom to selection (frames it in the viewport).
3. `screenshot` and save it under your **project/working dir** (e.g.
   `./figma-shots/stat-card.png`), named by component. This is your ground truth
   for the fidelity check in §7.

Coordinates you read off the returned screenshot map ~1:1 to clicks (the tool
handles the device-pixel ratio), so you can click canvas elements by eye. **To
read something small (an icon, a tiny label), do NOT use the `zoom` screenshot
action — it's unreliable here. Instead make the element big: select it, press
`Shift+2` so Figma zooms the canvas, then screenshot at that zoom.**

## 5. Icons → get the exact Figma vector (don't substitute by name)

Icons are design artwork; **fidelity means the actual Figma icon, not a
lookalike.** Figma icon layers are usually named `<category>/<solid|line>/<name>`
(e.g. `navigation/solid/home`), which tells you *which* icon and the solid/line
variant — use it to identify the icon and find its export. But **a same-named icon
already in the project is often a different drawing**, so reusing project icons by
name alone can leave the UI visibly off from the design. So:

1. **Get the real vector from Figma.** Select the icon → inspect **Export** → SVG
   → *Export* (a download needs the user's OK), then `Read` the `.svg` and inline
   it. Do this for **each** icon that's part of the deliverable. (You can't read
   "Copy as SVG" back — clipboard is blocked.)
2. **Reuse an existing project icon ONLY after a clean visual diff — else export.**
   Zoom both the Figma icon and the candidate project icon (`Shift+2`) and compare
   glyph, weight, and solid/line — keep it **only if identical**. If the zoom read
   is unreliable (it often is on the Figma canvas), **don't declare a match from a
   blurry glance — export instead.** Name-match ≠ visual-match.
3. **When you author/inline one, mirror the project's icon-file structure** — how
   its icon component applies color. **A path's own `fill` attribute (`"none"`,
   `"white"`, a hex) overrides the color the component injects** — so the icon
   renders white/invisible or loses its cut-out details (an evenodd hole fills in).
   Match the project's convention (often a `fill=""` placeholder the component
   fills, so color inherits down) and pull the icon's color (active vs. inactive
   states differ) and size from inspect.
4. **Verify each icon actually renders in the running app** (§7) — right color,
   right glyph, cut-outs intact. **Never batch-declare "icons ✓" from Figma
   alone**: a broken path-`fill` shows white/invisible only in the app, never in
   Figma, so it slips past a canvas-only comparison.

Match `width`/`height`, color, and the solid/line variant to the inspect values.
Reusable-icon-component pattern in [implementation.md](references/implementation.md).

## 6. Implement (map the design, keep it simple)

Build to the **project's** conventions and design system first; use Figma values
where the project has no token. Don't overcomplicate — mirror the design's own
structure, no more. See [implementation.md](references/implementation.md) for the
full autolayout→CSS table, the component-decomposition method, and framework
notes. The essentials:

- **Layout — flex by default, grid when it's a real 2D/wrapping grid.** Figma
  autolayout is 1-D, so it maps to **flexbox**. Reach for **CSS grid** only when
  the design is a genuine grid (a wrapping card gallery, an N-column layout that
  reflows). Take `flex-direction`, `justify-content`, `gap`, and `padding`
  straight from the parent frame's inspect.
- **Padding/margins stay sound because Figma puts spacing on the container, not
  the children.** An autolayout frame owns its **padding** (all four sides) and
  the **gap** between children; children carry **no margins**. Replicate that:
  container gets `padding` + `gap`; children get `margin: 0`. This is the single
  rule that keeps spacing correct and avoids margin-collapse guesswork.
- **Component structure from the tree.** Each named frame → a component. Its
  variant **Component properties** → props. Repeated children → a mapped list with
  a data prop. Parent owns layout + spacing; children own their own content and
  padding. Keep the prop surface as small as the design's variants.
- **Typography & radius exactly.** Use the exact `font-family`, `font-weight`
  (numeric), `font-size`, `line-height`, `letter-spacing`, and `border-radius`
  from §3 — no rounding. If the font is a web/Google font (e.g. Inter Tight),
  ensure it's actually loaded via the project's font mechanism (don't just name
  it and hope). Prefer the design-system token name (`Heading 3 Medium`, `Gray/Gray
  900`) **when the project actually defines it (verify — §0)**; if the token is
  missing, add it to match the spec — never reference a class that doesn't exist.
- **Colors** by token name where the project has one, else the hex from §3.

## 7. Verify 100% fidelity (screenshot diff loop) + edge cases

Fidelity isn't done until you've **compared your render to the Figma
screenshot**, not just read the code:

1. Screenshot the **running app** (the second tab, §1) at the design frame's
   width (read it from the frame's inspect — desktop frames are often ~1440px);
   reload after your edits.
2. **Read the truth with `getComputedStyle`, not just your eyes** — the single
   most reliable check. For each element you touched, eval it on the running app
   and compare the numbers to the extracted Figma spec (`fontSize`, `fontWeight`,
   `fontFamily`, `color`, `fill`, `padding`, `gap`, `border`, `borderRadius`). It
   catches what a screenshot can't: a class that silently no-ops (referenced but
   undefined), a color left at the old token, an icon still white.
   ```js
   const s = getComputedStyle(document.querySelector('<selector>'));
   JSON.stringify({fontSize:s.fontSize, fontWeight:s.fontWeight, color:s.color, fill:s.fill, borderRadius:s.borderRadius, padding:s.padding})
   ```
   **Confirm your overrides actually applied.** Styling through an existing
   component's `className`/prop can be silently clobbered by its default classes
   (CSS source-order without `tailwind-merge`); if computed styles show the old
   value, fix the component to merge classes — not just the call site.
3. **Then compare per element at high zoom** — for shape, layout, and icon
   fidelity the numbers don't cover; not a full-page glance. **Be adversarial:
   assume ≥3 things are off and hunt for them** — a pass that finds nothing means
   you didn't look hard enough. Walk the commonly-missed list below.
4. Fix the diffs, re-verify, repeat until they match. State any deliberate
   deviation and why.

**Commonly missed — check each one explicitly (a full-page glance skips all of
these):**
- **Text color of *every* label**, not just the primary value — titles and
  secondary labels are easy to leave at the project's old color.
- **Alignment inside rows** — a badge/label that should be right-aligned and
  vertically centered but drifts (you extracted `Align`/`Justify` in §3 — apply
  them, don't eyeball).
- **Sub-components — enumerate them all.** Before a component is "done", list its
  parts (title, value, dropdown/menu, count badge, chip, icon, border) and check
  each; one slipping through (a time-range dropdown, a badge) is the common tail.
  Match each part's fill/border/radius/typography and count value.
- **Borders present vs. absent, and exact gaps** — don't *infer* structure (e.g.
  bordered vs. borderless rows); confirm each stroke and gap against inspect, and
  **re-verify structural choices carried over from a previous pass** — an
  unconfirmed "borderless rows" guess persists until you actually check it.
- **Icons are the real Figma artwork (§5), and each renders correctly in the app**
  — right color and cut-outs, not white/invisible; a broken path-`fill` shows only
  in the running app, never in Figma.

**Cover the edge cases the static frame doesn't show:**
- **Overflow / scroll** — long lists, many chips, long names. Decide scroll vs.
  truncate vs. wrap; add `min-width:0`/`overflow` so flex children can shrink and
  ellipsize instead of blowing out the layout.
- **Tooltips / hover / focus / active / disabled / empty / loading** states —
  the frame shows one state; check sibling frames (designers often include an
  "empty" or "loading" variant) and implement the rest.
- **Overlap / z-index** — badges, avatars, dropdowns, sticky headers, modals.
- **Responsive** — if the file has both desktop and mobile frames, extract both
  and set breakpoints; otherwise build to the given frame and keep it fluid
  (Fill→`%`, not fixed px).

## 8. Deliverable

- The implemented component/screen in the project's conventions.
- A short note per component tying it to Figma: node name + `?node-id=<id>` deep
  link + the `figma-shots/*.png` you compared against + any deviation.
- Close the tab when done (`tabs_close_mcp`) unless the user wants it open.

## Tooling

Primary tools are the Claude-in-Chrome MCP (`mcp__claude-in-chrome__*`). If
deferred, load them in **one** `ToolSearch` call:

```
select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__browser_batch
```

Use `browser_batch` to chain click → key → screenshot in one round trip. Use
`javascript_tool` for all spec extraction (never touching location/cookies).

## Work efficiently (don't be noisy)

- **Extract, don't eyeball.** Every number that matters (font, size, leading,
  tracking, radius, padding, gap, hex) is in the inspect panel — read it once.
  Screenshots are for *look*, not for reading values.
- **Inventory the project's tokens/icons first (§0)** and `grep` each before use —
  mapping to a non-existent class/token is a silent fidelity bug.
- **Select → Shift+2 → screenshot** is the whole framing routine. Don't hand-pan
  or hand-zoom the canvas, and don't use the `zoom` screenshot action for detail.
- **Select on the canvas (double-click to drill) and verify the node name** before
  extracting — Layers-row clicks often mis-hit.
- **Batch** click/key/screenshot with `browser_batch`; check the cheap JS state
  before spending a screenshot.
- **Don't re-extract or re-shoot an unchanged selection.** Act, then verify once.
- **Build to project conventions**, reuse existing components/tokens, don't add
  icon/font packages the project doesn't already use.

## Reference files
| File | When to read |
|------|--------------|
| [references/implementation.md](references/implementation.md) | Full autolayout→flex/grid mapping table, Fixed/Fill/Hug→CSS, component-decomposition method, typography/font-loading, reusable SVG-icon pattern, framework notes, fidelity-diff checklist |
| [references/troubleshooting.md](references/troubleshooting.md) | Access/login walls, Dev Mode locked, the `location`/cookie JS block, blocked clipboard, canvas won't render, coordinate mapping, panel extractor returns nothing |
