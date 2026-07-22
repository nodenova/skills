---
name: miro-board-explorer
description: >-
  Read and extract the real content of a Miro board from its share link by
  driving agent-browser live; no one-shot script can gather a board for you.
  Use when the user gives a miro.com/app/board/... link (often with
  ?moveToWidget=...) and wants its change requests, comments, mockup
  annotations, or a page summarized or turned into a dev task/file. The skill
  encodes the moves that stop an agent from flailing: board mockups are
  WebGL-canvas pixels read via screenshots, but comments and frame names live in
  the DOM via `snapshot` and Miro's Activity/Frames panels — read those text
  sources first; click by ref, not pixel coordinates (the screenshot you view is
  downscaled, so pixel clicks miss); Miro keyboard zoom shortcuts do NOT register
  — use the on-screen zoom/fit buttons (ctrl+wheel overshoots into blank canvas);
  don't re-open the URL to navigate (it reloads to an empty canvas) — pan/zoom in
  the live session and map the annotations once before reading; the board hangs on
  a splash unless you spoof a real Chrome user-agent; and — the one that silently
  ruins runs — a `<canvas>` element exists ~45s BEFORE Miro paints into it, so
  gate every screenshot on the board actually having painted, never on the canvas
  existing. Triggers include "change requests on this miro", "summarize this miro
  page", "extract from this miro".
allowed-tools: Bash(agent-browser:*), Bash(curl:*), Read
---

# Miro Board Explorer

Drive `agent-browser` **live** to read a Miro board and produce something a dev
can act on. This is interactive: you open the board once, then look → decide →
act → look again, adjusting zoom/pan/panels as you go. **There is no script that
gathers a board for you — don't try to write one.** Keep one session (`--session
miro`) for the whole task and run `agent-browser` commands directly.

## Read this before you start (saves ~10 minutes of flailing)

A Miro board has **two kinds of content, and you read them differently:**

1. **Text that lives in the DOM — read it with `snapshot`, not your eyes.**
   - **Comments** (Activity panel): on change-request boards, *the comments are
     usually the change requests*. They are exact, attributed text. **Check
     these FIRST.**
   - **Frame names** (Frames panel): the board's table of contents / "pages".
   - App chrome (toolbar, zoom controls, search) — all DOM, all clickable by ref.
2. **The mockup art itself — read it from screenshots (vision).**
   - Shapes, sticky notes, and **handwritten/red annotations drawn on the
     canvas** are WebGL pixels. `agent-browser screenshot` captures them at full
     fidelity; zoom in until legible, then read the image.

So: **mine the text sources first** (comments + frames), *then* screenshot the
canvas for the visual mockups and annotations the text didn't cover. Don't try
to read everything off pixels — you'll waste turns.

Three more rules that prevent the dead-ends seen in real runs:

- **Never screenshot before the board has PAINTED.** A `<canvas>` element is in
  the DOM ~45 seconds before Miro draws the board into it. Screenshots taken in
  that window are blank white or a grey skeleton, and they look enough like
  "a board that has nothing on it" that runs have read them as real and produced
  confident output grounded in nothing. Use the `board_ready()` gate in step 1.
- **Click elements by `@ref` from `snapshot`, not by pixel coordinates.** The
  screenshot image you view is downscaled (e.g. 800px wide) from the real
  viewport (1600px), so coordinates you eyeball are ~2× off and your clicks
  miss. Refs have no such problem. (If you *must* use coordinates, multiply by
  `viewport_width / displayed_image_width`.)
- **Miro keyboard zoom shortcuts (`Alt+1`, `Ctrl+=`, arrows) do NOT register**
  on the canvas. Zoom with the on-screen **Zoom in/out / Fit-to-screen buttons
  (by ref)** — they step predictably. **ctrl+wheel overshoots to 1000%+ into
  blank canvas, so avoid it.** Don't waste turns pressing keys.

## 1. Open the board (the one fiddly setup)

Miro stalls forever on the yellow splash under default headless settings (bot
detection), and never fires a normal load event. Spoof a real Chrome UA, then
**poll until the board has actually PAINTED** — not merely until a `<canvas>`
exists:

```bash
export AGENT_BROWSER_USER_AGENT="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
export AGENT_BROWSER_ARGS="--disable-blink-features=AutomationControlled"
export AGENT_BROWSER_DEFAULT_TIMEOUT=90000

# Ready = a full-size canvas EXISTS *and* Miro's accessibility overview has
# populated. That text (document.body.innerText) jumps from ~16 to 400+ chars at
# the exact moment the canvas paints, and it is the only signal that does.
# Canvas-count alone opens ~45s TOO EARLY; document.title resolves ~32s too early.
board_ready() {
  agent-browser --session miro eval '(() => {
    const canvas = [...document.querySelectorAll("canvas")].some(c => c.width > 600 && c.height > 400);
    return canvas && document.body.innerText.length > 200;
  })()' 2>/dev/null | grep -q true
}

agent-browser --session miro set viewport 1600 1000
agent-browser --session miro open "<board-url>" >/dev/null 2>&1   # 'open' itself times out — that's NORMAL, ignore it

waited=0
until board_ready; do
  if [ $waited -ge 180 ]; then echo "board never painted after ${waited}s — see troubleshooting"; break; fi
  sleep 5; waited=$(( waited + 5 ))
done

agent-browser --session miro screenshot ./miro-shots/00-loaded.png   # Read it: where did the link drop you?
```

**Expect the wait to be 50-60s on a cold load.** Measured on a real board: canvas
element appears at ~10s, board paints at ~53s. Don't shorten it, and **don't
screenshot inside the loop** — a shot taken before the gate opens is a blank
white frame or a grey skeleton, and reading it costs a turn plus vision tokens
for nothing.

**There is a half-rendered state, and it is the dangerous one.** Miro resolves
the board in two waves: shapes, red ink and handwritten annotations paint
*first*, and the **mockup text stays blurry and unreadable for another ~8s**. A
shot taken then looks convincingly like a real board — you'd read the
annotations fine — but every UI string on it is a smear, so any copy you
"transcribe" from it is invented. `board_ready()` already excludes this state
(measured: `innerText` is 187 while blurry, 413 once text is crisp); that's
precisely why the threshold is 200 and not lower. **Don't lower it.**

**Sanity-check the file size before you Read the image — it's free**, but know
what it can and cannot tell you. At the `1600 1000` viewport this skill sets:
blank ≈ 11 KB, grey skeleton ≈ 15 KB, fully rendered ≈ 265 KB.

```bash
ls -l ./miro-shots/00-loaded.png    # under ~50 KB => nothing painted, keep waiting
```

That is a **blank/skeleton detector only — never a readiness signal.** The
blurry half-rendered frame above measures ~332 KB, *larger* than the finished
265 KB, so "bigger file" does not mean "more ready". `board_ready()` is the
authority; `ls -l` only saves you from Reading an empty frame. (Sizes scale with
viewport — at a smaller viewport a skeleton can be ~10 KB, so re-baseline the
floor if you change `set viewport`.)

**Never test paint with `gl.readPixels()`.** Miro allocates a 4096×4096 backing
canvas; reading pixels back from it pushed a 4 GiB container over its memory
limit and the OOM killer took the whole browser down mid-run (reproduced twice).
The `board_ready()` DOM check above costs nothing. For the same reason, if the
browser dies *at the moment the board paints*, suspect the container memory
limit, not the board — SwiftShader software rasterization peaks at ~3.4-4 GiB.

`<board-url>` is exactly what the user gave you, including any
`?moveToWidget=<id>` — that param centers the initial view on the item they care
about, so you land near it. Get the board name for free:
`curl -s "<board-url>" | grep -o 'og:title" content="[^"]*"'`.

If the board never paints, it's bot detection, a blocked CDN, or a private
board — see [references/troubleshooting.md](references/troubleshooting.md).

## 2. Mine the text sources (do this before screenshotting mockups)

```bash
agent-browser --session miro snapshot | grep -iE 'comment|activity|frame|fit|zoom|search' -n
```
That gives you refs for the panels. Then:

- **Comments → the change requests.** Click the **Activity** button, expand
  **All comments**, and toggle **Show resolved** (a request may be resolved).
  Read every comment as text — author, date, and which screen it's pinned to.
  ```bash
  agent-browser --session miro click @<activity-ref>
  agent-browser --session miro snapshot | grep -iE 'comment|@|resolved|May|generic' 
  ```
- **Frames → the page list.** Click the **Frames** button to enumerate frame
  names (the board's "pages"). Find the page the user named (e.g. "Meetings").
  If it isn't a named frame, it's a free-floating mockup — locate it visually in
  step 3.

Quote what you read here verbatim in your output; it's the most reliable
material on the board.

## 3. Read the mockup + annotations (vision)

**You land on the target from the initial `open`.** For a **single page**, stay
there and move with local pan/zoom — re-opening just to nudge a little is a
wasteful 50-60s cold reload. **But for a large multi-screen cluster (or when the
user gave several `?moveToWidget=` links), re-opening a widget link is the *most
reliable* way to jump to a distant screen or recover when you get lost panning** —
it lands you centered at ~30%. Treat the provided links as anchors.

Whenever you re-open: re-run **`board_ready()`** from step 1 (never a blind
`sleep`, and never the bare canvas-count check — that opens ~45s early and hands
you a skeleton). A re-open is a full cold load: **budget 50-60s** before anything
is worth capturing, then confirm the PNG is >20 KB before you Read it. (Red ink /
annotations usually paint *before* mockup textures, so you can often read the
notes even while the mockup is still gray.)

Read the canvas in **two passes — map first, then read each item once.** This is
the single thing that stops the back-and-forth:

**Pass A — map the FULL extent first.** Don't build the checklist from the
landing view alone — **the `moveToWidget` point is often the *edge* of the
page's cluster, not its center**, so the landing view can hide annotations off to
one side. Zoom out (or pan across) until **every red mark for this page is in one
frame at once**, even as unreadable blobs, and count them — that count is your
checklist. Note which mockup each sits next to. Two traps that cause silent
misses:
- **Annotations usually sit *beside* the screen they describe**, not on it — so a
  screen with no ink on it can still have a note floating to its left/right.
  "I panned past a screen and saw no ink on it" is not coverage.
- **On-screen affordances are tells.** A badge ("Notes available"), an extra tab,
  a recording/transcript control, an empty-vs-populated pair of the same screen —
  each usually has a gating annotation nearby. If you see one, hunt for its note.

**Pass B — read each once.** For every item on the list, zoom to a legible level
(≈150-200%) on that cluster, screenshot, transcribe the text **verbatim**, check
it off. Don't re-screenshot a cluster you've already read. **If an annotation is
clipped at the viewport edge, zoom out one step to fit it whole — don't nudge the
pan a little at a time** (that's a trial-and-error loop of 4-5 shots; one zoom-out
usually frames the entire note in a single shot, readable at a lower level).

**Before you declare done, your read count must equal your mapped count.**
Re-zoom to the full-extent view and confirm every red region is accounted for.
"I panned right and the screens had no annotations" is **not** a completeness
check — annotations offset from their screen are exactly what it misses.

**When the cluster is too big to fit legibly in one frame** (a whole flow of many
screens, or several widget links), you can't map it in a single shot — at the zoom
where it all fits, the ink is unreadable. So:
1. Take one fit-to-screen / low-zoom shot just to see the **layout** — how many
   screens, how many rows, roughly where the ink clusters are. This is a rough
   inventory, not a read.
2. Treat each provided `?moveToWidget=` link as a guaranteed anchor. Visit each by
   re-opening it; read that screen + the annotations immediately around it at a
   legible zoom (~30-50%) with only small right-drags; then move to the next anchor
   by **re-opening it — don't pan across the whole canvas between distant screens**
   (that's where runs get lost and burn 20+ shots).
3. For screens *between* anchors, right-drag locally at 30-50%. If you lose your
   place, re-open the nearest anchor rather than hunting blindly.
The completeness rule still holds: count the screens / annotation regions you must
cover, and check each off.

**Zoom with the on-screen +/- buttons only:**
```bash
agent-browser --session miro snapshot | grep -iE 'zoom in|zoom out|%' -n   # refs + current zoom %
agent-browser --session miro click @<zoom-in-ref>     # gentle, ~1 step per click; repeat
```
**Re-grep these refs before each zoom click** — Miro renumbers toolbar refs
whenever any panel or menu opens/closes, so a cached `@ref` silently clicks the
wrong control (or nothing). The buttons also zoom toward the **viewport center**,
so center your target first (right-drag), then click zoom-in.
The buttons step predictably. **Avoid ctrl+wheel — it jumps ~1.5×/tick and
overshoots to 1000%+ in two or three ticks, dumping you in empty canvas**, after
which you burn turns clawing back. To reset, open the zoom-% menu → **Fit to
screen / Zoom to 100%**.

**Know your zoom before you shoot — cheaply.** The current zoom % lives in the DOM
(bottom-right). Read it with text (≈free) instead of spending a screenshot to
discover you're at 2000%:
```bash
agent-browser --session miro snapshot | grep -oE '[0-9]+%' | tail -1
```
If it's absurd (>400% or <25%), fix the zoom before you screenshot. More
generally: **before any screenshot that follows a reload or a zoom change, check
cheaply (board painted, zoom sane) that the view is worth capturing.** A blank
screenshot still costs a turn and vision tokens.

**Panning — the mechanics are non-obvious, and getting them wrong wastes dozens of
shots.** Miro does **not** pan the way you'd expect from the mouse wheel:
- **Horizontal pan:** `mouse move 800 500`, then `mouse wheel 0 <dx>` — the second
  arg (`dx`) pans left/right cleanly.
- **Vertical pan — and the reliable all-purpose pan — is a RIGHT-button drag, not
  the wheel:** `mouse move x1 y1` → `mouse down right` → `mouse move x2 y2` →
  `mouse up right`. The view follows the cursor (drag down reveals content below).
  **The vertical wheel (`mouse wheel <dy> 0`) ZOOMS on Miro — it does not pan** —
  so never use `dy` to move up/down. A *left*-button drag selects the frame instead
  of panning (even in Comment-only mode), so don't use it to navigate.
- **Low-zoom panning overshoots — even at 15-50%, not just <5%.** A screen-space
  drag moves `drag_px / zoom_fraction` in world units, so at 30% a 500px drag jumps
  ~1600 world px — straight past your target into blank canvas (this burned ~8
  shots in a real run). Two rules: keep drags **small** (100-200px) at low zoom,
  and **change either zoom OR pan per shot, never both** — a pan+zoom combo
  compounds the overshoot.
- **To read an annotation clipped at the edge, prefer NOT panning at all.** In
  order: (a) **zoom out one step** to fit the note, or (b) **widen the viewport**
  (e.g. `set viewport 1900 950 1`) so both the mockup and its side-annotations fit
  in one shot. Both beat the fragile pan-to-reveal loop. (Widen-the-viewport was
  the move that finally un-stuck a real run — use it proactively, not as a last
  resort.)
- Clicking a comment pin or a frame recenters *exactly* — prefer it over guessing.
- **Viewport & the image-size limit (this errors out runs):** a screenshot's pixel
  width is `viewport_width × dpr`, and if it exceeds ~2000px the image **fails to
  process** ("an image … could not be processed"). So keep `viewport_width × dpr
  ≲ 1900`:
  - **1× (default):** viewport up to ~1900 wide is safe — use this for wide reads.
  - **2× retina** (sharper small text): viewport must be **≤ ~960 wide** — so only
    use retina zoomed into a *small* region, never at a wide viewport.
  If a shot errors, you exceeded it — drop dpr to 1 (or narrow the viewport) and
  re-shoot.

See [references/extraction-playbook.md](references/extraction-playbook.md) for
the full method, board search, and panning details.

## 4. Write the deliverable

Produce structure, not pixel descriptions. Tie each point to its evidence:

```
# <Board title> — <page> change requests

Source: <board-url>   Screenshots: ./miro-shots/

- <change> — from comment by <author> (<date>) / red annotation on <page>
  ref: <board-base-url>/?moveToWidget=<id>   shot: <page>-1.png
- ...

## Open questions / ambiguities
<things implied but not explicit>
```

Keep a `?moveToWidget=<id>` deep link per item so a human can verify your
reading. When done: `agent-browser --session miro close`.

## Work efficiently (the agent was too noisy last time)

- **Map first, then read each item once** (§3). Most of the flailing in past runs
  was pan-and-peek with no map plus re-reading the same annotation — a single
  overview shot replaces all of it.
- Prefer **text sources over pixels**, and **refs over coordinates** — both cut
  failed attempts.
- **Don't re-open to navigate, and don't ctrl+wheel to zoom** — both produce blank
  screenshots. Stay in the live session; zoom with the +/- buttons.
- **Look cheaply before you shoot:** `board_ready()` and the zoom-% are text reads
  (≈free); `ls -l` on the PNG is free. Spend a vision token only on an image you
  already know is worth reading.
- `grep` the `snapshot` output for what you need instead of dumping the whole
  tree every time.
- Don't re-screenshot or re-read an unchanged view. Act, then verify once.

## Reference files
| File | When to read |
|------|--------------|
| [references/extraction-playbook.md](references/extraction-playbook.md) | Full explore→read→summarize method: comments/frames panels, board search, panning, reading mockups, dev-handoff format |
| [references/troubleshooting.md](references/troubleshooting.md) | Stuck on splash, blank/skeleton screenshots, bot detection, blocked CDN, private boards, why keyboard zoom fails, the downscaled-coordinate trap |
