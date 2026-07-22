# Extraction playbook

The full interactive method. You run `agent-browser --session miro` commands by
hand, looking at output between steps. Order matters: **text sources first
(cheap, exact), pixels last (expensive, fuzzy).**

## 0. Working folder
Save screenshots under your **project/working directory**, not the skill folder
(e.g. `./miro-shots/`). Name them by content so they double as evidence:
`meetings-1.png`, `payment-detail.png`. Read every shot before moving on —
but `ls -l` it first: at the `1600 1000` viewport, **under ~50 KB means nothing
painted** (blank ≈11 KB, grey skeleton ≈15 KB, rendered ≈265 KB), so don't spend
vision tokens on it. Size is a blank detector *only* — the blurry half-rendered
frame is ~332 KB, bigger than the finished board, so never read "large" as
"ready". `board_ready()` decides that.

## 1. Identify the board (no rendering)
```bash
curl -s "<board-url>" | grep -oE '<meta property="og:(title|url)" content="[^"]*"'
```
`og:title` is the board name — use it as your heading.

## 2. Open once, then stay in the session
See SKILL.md step 1 for the exact open + `board_ready()` recipe. **The gate is
"the board has painted", not "a canvas exists"** — the element shows up ~45s
before Miro draws into it. After the board paints, do **not** re-open for every
move — navigate within the live session.

## 3. Comments = the change requests (read these first)
On boards used for design review, the actual requests are Miro **comments**, and
they are real DOM text — far more reliable than reading handwriting off pixels.

```bash
agent-browser --session miro snapshot | grep -niE 'activity|comment'
agent-browser --session miro click @<activity-ref>          # open the Activity / comments panel
agent-browser --session miro snapshot | grep -iE 'all comments|show resolved'
agent-browser --session miro click @<all-comments-ref>
# read them:
agent-browser --session miro snapshot | grep -iE 'comment|@|generic "|resolved'
agent-browser --session miro scroll down 600                # the panel scrolls; repeat to load more
```
- Toggle **Show resolved** — a request may already be marked resolved but still
  describe intended work.
- For each comment capture: author, date, the text verbatim, and which screen/
  area it's pinned to (the panel usually names or previews the target).
- Comments pin to board locations; clicking one recenters the canvas there,
  which is a fast way to jump to the relevant mockup.

## 4. Frames = the board's table of contents
```bash
agent-browser --session miro snapshot | grep -niE 'frame'
agent-browser --session miro click @<frames-ref>
agent-browser --session miro snapshot | grep -oE 'option "[^"]*"' | sort -u   # the frame/page names
```
Match the page the user named (e.g. "Meetings"). If no frame has that name, it's
a **free-floating mockup**, not a frame — find it with the user's `moveToWidget`
link or by panning. (There may also be an **"Explore board content" / outline**
feature that lists structure — check the snapshot for it. Its presence is also
the signal `board_ready()` keys on: that outline text only populates once the
board has actually painted.)

## 5. Navigate to a region
The panning mechanics on Miro are non-obvious — getting them wrong is the single
biggest source of wasted shots. Move in this order of preference:
- **Horizontal pan:** `mouse move 800 500`, then `mouse wheel 0 <dx>` (the `dx`/
  second arg pans left-right). **The vertical wheel `mouse wheel <dy> 0` ZOOMS, it
  does NOT pan** — never use it to move up/down.
- **Vertical pan (and the reliable all-purpose pan): RIGHT-button drag** —
  `mouse move x1 y1` → `mouse down right` → `mouse move x2 y2` → `mouse up right`.
  View follows the cursor (drag down reveals content below). A **left**-drag selects
  the enclosing frame instead of panning (even in Comment-only mode), so don't use
  it to navigate.
- **Don't fine-position at <5% zoom** — every drag overshoots into blank canvas.
  Zoom to ~25-50% first, then drag.
- **From a panel (exact recenter):** click the frame in the Frames panel, or a
  comment in Activity — both recenter the canvas precisely, no guessing.
- **Re-open the deep link — the reliable anchor for big clusters / when lost:**
  re-opening `"<base>/?moveToWidget=<id>"` lands you centered (~30%) on that exact
  screen. For a *single small page* it's a wasteful cold reload, so pan locally
  instead. But for a **large multi-screen cluster** (or multiple provided links),
  jumping between distant screens by re-opening beats panning across the canvas.
  Always re-run **`board_ready()`** (SKILL.md step 1) — **never a blind `sleep`,
  and never a bare canvas-count check** — and budget **50-60s** for the reload.
  Get an id via right-click item → **Copy link**.

## 6. Zoom — on-screen buttons, never keyboard or ctrl+wheel
Keyboard zoom shortcuts do **not** register on the Miro canvas. Zoom with the
**on-screen +/- buttons** — they step predictably and never overshoot:
```bash
agent-browser --session miro snapshot | grep -iE 'zoom in|zoom out|fit|%'   # refs + current zoom %
agent-browser --session miro click @<zoom-in-ref>     # or @<zoom-out-ref>, @<fit-to-screen-ref>
```
**Re-grep the zoom refs before each click** — Miro renumbers toolbar refs whenever
any panel or menu opens/closes, so a cached `@ref` clicks the wrong control or
nothing. The buttons zoom toward the **viewport center**, so center your target
with a right-drag first, then zoom in.

"Fit to screen" is often behind the zoom-percentage menu — open that menu, then
click it. It resets the view to the whole board (useful to re-orient when you've
zoomed into empty canvas).

**Read the current zoom cheaply** (so you don't screenshot blind):
`agent-browser --session miro snapshot | grep -oE '[0-9]+%' | tail -1`.

**Avoid ctrl+wheel.** It zooms ~1.5×/tick and overshoots to 1000-2000% in two or
three ticks, landing you in empty canvas — then you waste turns zooming back. The
buttons are slower per click but never overshoot. If you ever do reach for it, one
tick at a time and read the zoom % after each:
```bash
agent-browser --session miro eval 'var c=document.querySelector("canvas"),r=c.getBoundingClientRect();c.dispatchEvent(new WheelEvent("wheel",{deltaY:-120,ctrlKey:true,clientX:r.width/2,clientY:r.height/2,bubbles:true}))'
```

## 7. Read mockups + annotations (vision)
Zoom until a human could read it, then `screenshot` and read the image. Sticky
notes, shape labels, connector/arrow direction, and red handwritten annotations
are all canvas pixels — quote them verbatim where they carry intent ("if logged
in →", status labels, ticket numbers). Colors often mean something (red = change
/ problem) but flag that as an assumption. Tile big regions with overlapping
shots. Default to a **1×** viewport (`set viewport 1500 950 1`); a 2× retina
viewport (`set viewport 1600 1000 2`) sharpens small text but at a wide viewport
the image can exceed the screenshot size limit and error out — use retina only
zoomed into a small region, and fall back to 1× if a shot fails to process.

**Never probe paint with `gl.readPixels()`.** Miro's backing canvas is 4096×4096;
reading it back OOM-killed a 4 GiB container mid-run (reproduced twice). Use the
free signals: `board_ready()` for paint, `ls -l` for "did this shot capture
anything".

**Clipped annotation?** If a note runs off the viewport edge, **zoom out one step
to fit it whole** rather than nudging the pan a little at a time — the nudge loop
burns 4-5 shots; one zoom-out usually frames the whole note in a single shot.

**Map the full extent before you read, and count to declare done** (SKILL.md §3).
The `moveToWidget` landing is often the *edge* of the cluster, and annotations sit
*beside* the screen they describe — so zoom out until every red mark is in one
frame, count them, then read each. A real run that skipped this missed 2 of 5
change requests: it panned past the right-side screens, saw no ink *on* them, and
declared the page done — while two recording-gating annotations sat just off to
the side. Don't repeat it: read-count must equal mapped-count.

## 8. Board search (locate known text fast)
When hunting a specific term rather than browsing, use Miro's on-board search
from the toolbar: `screenshot --annotate` to get a clickable ref for the search
icon, click it, type the term, screenshot the results; clicking a result
recenters the board on that item.

## 9. Deliverable
Structure it (see SKILL.md step 4): current state, requested changes (each tied
to a comment author/date or annotation + a `moveToWidget` deep link + a
screenshot file), and open questions. State assumptions explicitly — a board is
a sketch and some intent is inferred. Close the session when done:
`agent-browser --session miro close`.
