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
  the live session and map the annotations once before reading; and the board
  hangs on a splash unless you spoof a real Chrome user-agent. A sign-up banner
  overlays the top-center of every screenshot, and a current-vs-redesign mockup
  pair is too wide to read in one shot — sweep it at a locked zoom. Triggers
  include "change requests on this miro", "summarize this miro page", "extract
  from this miro".
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

Two more rules that prevent the dead-ends seen in real runs:

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
**poll for the `<canvas>`** instead of trusting `open`/`networkidle`:

```bash
export AGENT_BROWSER_USER_AGENT="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
export AGENT_BROWSER_ARGS="--disable-blink-features=AutomationControlled"
export AGENT_BROWSER_DEFAULT_TIMEOUT=90000
agent-browser --session miro set viewport 1600 1000
agent-browser --session miro open "<board-url>" >/dev/null 2>&1   # 'open' itself times out — that's NORMAL, ignore it
# Poll until the canvas renders (cold load takes 20-90s):
until agent-browser --session miro eval 'document.querySelectorAll("canvas").length' 2>/dev/null | grep -qE '[1-9]'; do sleep 3; done
agent-browser --session miro screenshot ./miro-shots/00-loaded.png   # Read it: where did the link drop you?
```

`<board-url>` is exactly what the user gave you, including any
`?moveToWidget=<id>` — that param centers the initial view on the item they care
about, so you land near it. Get the board name for free:
`curl -s "<board-url>" | grep -o 'og:title" content="[^"]*"'`.

**Anonymous vs signed-in.** This recipe opens *anonymously* (top-right reads
"Comment only"). Fine for a quick read — but Miro then pins a **"Continue
collaborating… / Sign up for free" banner over the top-center of the canvas**,
occluding a ~500px-wide strip in *every* screenshot (§3). For a **large
multi-widget job**, open with a persisted `--profile` and sign in once: the
banner disappears and the cache warms, so re-opening anchors — your main
multi-widget navigation move (§3) — drops from a 20-90s cold load to a few
seconds. Same `--profile` mechanism as the private-board path in
[troubleshooting](references/troubleshooting.md).

If the canvas never appears, it's bot detection, a blocked CDN, or a private
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
wasteful 20-90s cold reload. **But for a large multi-screen cluster (or when the
user gave several `?moveToWidget=` links), re-opening a widget link is the *most
reliable* way to jump to a distant screen or recover when you get lost panning** —
it lands you centered at ~30%. Treat the provided links as anchors.

Whenever you re-open: re-run the canvas poll from step 1 (never a blind `sleep`),
**then confirm the mockup actually painted before reading.** A passing canvas
count can still show gray skeleton boxes for a few seconds — if the shot is
skeleton, wait and re-shoot. (Red ink / annotations usually paint *before* mockup
textures, so you can often read the notes even while the mockup is still gray.)
**Mockup textures are lazy, per-zoom tiles** — a region can sit gray at a deep
zoom while the *same* mockup is already painted one step out (its lower-res tiles
were cached earlier). So if a high-zoom shot is skeleton, **zoom out one step and
re-shoot** instead of only waiting; and because the ink paints first, most change
requests are legible even if the UI underneath never finishes painting.

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

**Content wider than one legible viewport — sweep, don't fit.** A design-review
page is often a *pair* — the current screen and its "# Change it to…" redesign
side by side — with annotations on the *outer* edges of both. That whole unit is
too wide to read in one shot: at a zoom where the ink is legible (~75-100%) it
overflows the ~1900px image cap, and zooming out to fit makes the handwriting
unreadable. So don't try to frame it all at once — **sweep it at a locked zoom:**
1. Pick a legible zoom and **lock it** — don't touch zoom again until the sweep
   ends (changing zoom mid-sweep brings back the pan+zoom overshoot).
2. Center the unit's **left edge**, screenshot.
3. Pan right with the horizontal wheel (`mouse move 800 500; mouse wheel 0 <dx>`)
   by a step that advances ~⅔ of a viewport, so the new shot **overlaps the
   previous by ~30%** (one landmark visible in both). Calibrate `dx` once on the
   second shot, then keep it fixed.
4. Repeat until you pass the unit's right edge.
Every annotation lands legible in *some* shot and the overlap guarantees nothing
hides in a seam. This is the fix for the recurring "the rename note was clipped,
treat it as best-guess" outcome — sweep instead of nudging the pan.

**A sign-up banner hides the top-center of every shot.** Anonymous sessions get a
~500px-wide "Sign up for free" banner pinned over the top-center canvas (§1).
Anything under it — an annotation, a mockup's title bar — is *silently* gone. If a
note seems to start mid-sentence at the top edge, it's clipped by the banner: pan
that content into the **clear middle** of the viewport (or sign in via
`--profile`) and re-shoot.

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
   (that's where runs get lost and burn 20+ shots — in past runs *every* recovery
   was a re-open, never a rescue-pan). If re-opens feel too slow to resist panning,
   that's the signal to open with a `--profile` (§1) so they're fast — not to start
   free-panning between widgets.
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
cheaply (canvas present, not loading, zoom sane) that the view is worth
capturing.** A blank screenshot still costs a turn and vision tokens.

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
- **Look cheaply before you shoot:** read canvas-ready / zoom-% with `eval` or
  `snapshot` (text) before spending a screenshot you then have to view.
- `grep` the `snapshot` output for what you need instead of dumping the whole
  tree every time.
- Don't re-screenshot or re-read an unchanged view. Act, then verify once.

## Reference files
| File | When to read |
|------|--------------|
| [references/extraction-playbook.md](references/extraction-playbook.md) | Full explore→read→summarize method: comments/frames panels, board search, panning, reading mockups, dev-handoff format |
| [references/troubleshooting.md](references/troubleshooting.md) | Stuck on splash, bot detection, blocked CDN, private boards, why keyboard zoom fails, the downscaled-coordinate trap |
