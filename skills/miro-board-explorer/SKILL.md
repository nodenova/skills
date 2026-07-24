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
  ruins runs — a `<canvas>` element exists 12-45s BEFORE Miro paints into it, so
  gate every screenshot on the board actually having painted, never on the canvas
  existing. It is also expensive on every platform: an open board pins a CPU core
  and gigabytes for as long as the tab lives (on a desktop that starves the
  machine; in a container it OOM-kills the browser), so run exactly ONE browser,
  close it the moment the reading is done, and sweep the orphaned browsers `close`
  cannot see. Timings differ per platform — check `uname -s` and use the right
  column. Triggers include "change requests on this miro", "summarize this miro
  page", "extract from this miro".
allowed-tools: Bash(agent-browser:*), Bash(timeout:*), Bash(curl:*), Bash(uname:*), Bash(ps:*), Bash(pgrep:*), Bash(pkill:*), Bash(grep:*), Bash(ls:*), Bash(mkdir:*), Bash(sleep:*), Read
---

# Miro Board Explorer

Drive `agent-browser` **live** to read a Miro board and produce something a dev
can act on. This is interactive: you open the board once, then look → decide →
act → look again, adjusting zoom/pan/panels as you go. **There is no script that
gathers a board for you — don't try to write one.** Keep one session (`--session
miro`) for the whole task and run `agent-browser` commands directly.

## 0. Know your platform, and know what an open board costs

**Run `uname -s` first** — it decides the numbers you work to, and both platforms
are supported. What is identical everywhere: the ready gate, one-instance
discipline, closing early, and the orphan sweep. What differs is the clock and the
way it hurts when you get it wrong.

| | **macOS desktop** (`Darwin`) | **headless Linux container** (`Linux`) |
|---|---|---|
| WebGL backend | real GPU — ANGLE Metal (verified) | SwiftShader **software** raster |
| cold load → painted | **~25s** | **~50-60s** |
| canvas exists before paint | ~12s early | ~45s early |
| RAM per open board | ~1.3 GB idle, ~3.5 GB while shooting | peaks 3.4-4 GB |
| CPU per open board | **~100% (a full core), forever** | ≥1 core, worse (software raster) |
| how it bites you | starves the whole machine; leaked browsers stack up | **OOM-kill at ~4 GiB** exactly when the board paints |
| extra setup | none | may need CDN/domain allowlist; `--no-sandbox`; xvfb |

Everything else in this skill is platform-neutral. Where a number appears below
without a platform, it holds on both.

**The cost model is the same on both: a parked board never idles down.** Miro's
render/sync loop runs as long as the tab exists, and viewport and zoom don't change
it (1600×1000 and 900×600 both measured ~104% CPU on macOS). There is no "make it
cheaper" knob — **the only lever is how long the tab stays open**, and the minutes
you spend thinking, writing up, or reading a screenshot are billed at the same rate.
Two instances cost double, which is how a Mac ends up unusable and how a 4 GiB
container ends up OOM-killed.

Rules that follow from it, on every platform:

- **Exactly one browser, one session (`--session miro`), one command at a time.**
  Never run agent-browser commands in parallel Bash calls.
- **Check before you open and after you close** (free, no vision cost — works on
  macOS and Linux; the `grep -v --type=` drops Chrome's helper processes):
  ```bash
  ps -Ao pid,command | grep "[a]gent-browser/browsers/chrome" | grep -v -- "--type=" | wc -l   # expect 0
  ```
- **`close` as soon as the reading is done.** Write the deliverable *afterwards*,
  from your notes and the saved PNGs — never hold the board open "in case".
- **Parking it costs more than a reload.** A cold re-open is ~25s (mac) / ~55s
  (container) of one core; a minute of parked board is ~60 core-seconds. About to
  think, write, or wait? Close first.
- **A killed or crashed run leaks a browser `close` cannot reap** — see
  [Cleanup](#5-cleanup-run-this-even-if-the-run-failed). Always finish there.

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
  the DOM ~12 seconds before Miro draws the board into it (~45s on a slow Linux
  container). Screenshots taken in that window are blank white or a grey skeleton,
  and they look enough like "a board that has nothing on it" that runs have read
  them as real and produced confident output grounded in nothing. Use the ready
  gate in step 1.
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

**Call 1 — launch. Every line below goes in ONE Bash call.** The user-agent and
launch flags are baked into the browser process by whichever `agent-browser`
command starts it, and **shell state does not survive to your next Bash call** —
so if `set viewport` (or anything else) starts the browser in a call that lacks
these exports, you get an unspoofed browser that hangs on the splash forever and
no error tells you why.

```bash
ps -Ao pid,command | grep "[a]gent-browser/browsers/chrome" | grep -v -- "--type=" | wc -l  # must be 0 — if not, Cleanup (§5) first
export AGENT_BROWSER_USER_AGENT="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
export AGENT_BROWSER_ARGS="--disable-blink-features=AutomationControlled"   # Linux container: add ",--no-sandbox" if Chrome won't start
mkdir -p ./miro-shots
agent-browser --session miro set viewport 1600 1000
timeout 25 agent-browser --session miro open "<board-url>" >/dev/null 2>&1   # 'open' always times out — NORMAL, ignore it
agent-browser --session miro eval 'navigator.userAgent' | grep -q Headless \
  && echo "UA SPOOF FAILED — close the session and redo this call as one block" || echo "UA ok"
```

(The Mac UA string works from Linux too — it's what you're claiming to be, not
what you're running on. Don't swap it for a Linux UA.)

**Call 2 — the ready gate. Poll in short calls, never one long one.** Ready = a
full-size canvas EXISTS *and* Miro's accessibility overview has populated;
`document.body.innerText` jumps from ~16 to 400+ chars at the exact moment the
canvas paints, and it is the only signal that does. There is no shell function
here on purpose — one defined in an earlier call is gone. Paste this block, and
if it doesn't print PAINTED, paste it again (macOS: usually one pass is enough;
container: expect 2, allow 3-4 before calling it a failure):

```bash
for i in $(seq 1 10); do
  [ "$(agent-browser --session miro eval '[...document.querySelectorAll("canvas")].some(c=>c.width>600&&c.height>400) && document.body.innerText.length>200' 2>/dev/null)" = "true" ] \
    && { echo PAINTED; break; }
  sleep 5
done
```

**Keep every Bash call comfortably under the tool timeout (~2 min).** A call that
overruns gets killed by the harness, and that can kill the agent-browser daemon
while leaving its Chrome alive — a headless browser rendering the board at 100%
CPU that `close` and `session list` can no longer see. That is the single most
expensive failure mode of this skill. The loop above is ≤50s by design; repeat it
rather than lengthening it.

Only once it prints PAINTED:

```bash
agent-browser --session miro screenshot ./miro-shots/00-loaded.png   # Read it: where did the link drop you?
```

**Cold load: ~25s on macOS, 50-60s on a Linux container** (measured: canvas at
~11s / paint at 23s on a Mac; canvas at ~10s / paint at ~53s in a container).
Allow ~90s (mac) / ~180s (container) before treating it as a failure. **Don't
screenshot inside the loop** — a shot taken before the gate opens is a blank
frame, and reading it costs a turn plus vision tokens for nothing.

**There is a half-rendered state, and it is the dangerous one.** Miro resolves
the board in two waves: shapes, red ink and handwritten annotations paint
*first*, and the **mockup text stays blurry and unreadable for another few
seconds**. A shot taken then looks convincingly like a real board — you'd read
the annotations fine — but every UI string on it is a smear, so any copy you
"transcribe" from it is invented. The gate already excludes this state — measured
`innerText` while blurry vs crisp was 111 → 414 on macOS and 187 → 413 in the
container, so the same threshold of 200 lands in the gap on both. **Don't lower
it.**

**Sanity-check the file size before you Read the image — it's free**, but know
what it can and cannot tell you. At the `1600 1000` viewport this skill sets, a
blank frame is ~10-11 KB and a grey skeleton ~13-15 KB on both platforms, so:

```bash
ls -l ./miro-shots/00-loaded.png    # under ~50 KB => nothing painted, keep waiting
```

That is a **blank/skeleton detector only — never a readiness signal.** The
half-painted frame measured 74 KB on macOS — well over the floor and a perfectly
real-looking image, while its mockup text was still unreadable. Nor is there a
"big enough" size that means ready: a rendered board measured ~130 KB (macOS, one
board at 23% zoom) and ~265 KB (container, another board), and in the container the
blurry frame came out at ~332 KB, *larger* than the finished one. So size varies
with board, zoom and platform, and "bigger" never means "more ready". The gate is
the authority; `ls -l` only saves you from Reading an empty frame. (Sizes scale
with the viewport, so re-baseline the ~50 KB floor if you change `set viewport`.)

**Never test paint with `gl.readPixels()`, on either platform.** Miro allocates a
4096×4096 backing canvas; reading pixels back from it pushed a 4 GiB container over
its memory limit and the OOM killer took the whole browser down mid-run (reproduced
twice). On a desktop it won't OOM, it just adds a big allocation and a GPU stall to
a browser that is already holding a core. The DOM gate above costs nothing — use it.

**If the browser dies at the moment the board paints, that's memory, not Miro** —
the container case: SwiftShader peaks at ~3.4-4 GiB against a 4 GiB cap. Raise the
limit, or free it up by making sure only one instance is running (§5).

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
there and move with local pan/zoom — re-opening just to nudge a little wastes a
full cold reload (~25s mac / 50-60s container, at 1-3 cores). **But for a large
multi-screen cluster (or when the user gave several `?moveToWidget=` links),
re-opening a widget link is the *most reliable* way to jump to a distant screen or
recover when you get lost panning** — it lands you centered at ~30%. Treat the
provided links as anchors; on a Mac the reload is cheap enough that being lost for
three pans is worse than re-anchoring, in a container it's the opposite.

Whenever you re-open: re-run **the ready gate** from step 1 (never a blind `sleep`,
and never the bare canvas-count check — that opens 12-45s early and hands you a
skeleton). A re-open is a full cold load, so budget the same as a first load, then
confirm the PNG is >50 KB before you Read it.

Red ink and annotations do paint *before* mockup textures — but that is a warning,
not a shortcut. It is exactly the blurry half-render from §1: the notes are
legible while **every UI string next to them is still a smear**. If you read that
frame, read *only* the annotations from it, and never transcribe mockup copy until
the gate has opened.

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
it off. Don't re-screenshot a cluster you've already read — besides the vision
tokens, each capture forces a GPU readback and PNG encode that roughly doubles the
browser's CPU draw while it runs (measured ~100% idle → ~200% during a shooting
loop). **If an annotation is
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

## 4. Close the board, THEN write the deliverable

The moment your read-count equals your mapped count, you are done with the
browser. Close it before you write anything — the write-up takes minutes, and a
parked board bills a core for every one of them:

```bash
agent-browser --session miro close
```

Everything you need is already in your notes and `./miro-shots/`. If you discover
a gap while writing, re-opening the anchor link costs one cold load — cheaper than
having held the board open the whole time.

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
reading.

## 5. Cleanup (run this even if the run failed)

`agent-browser` runs a detached daemon that owns the Chrome process. `close` (and
`close --all`) goes through that daemon, so it only reaps browsers whose daemon is
still alive. **If the daemon dies abnormally — a Bash call killed on timeout, a
crash, an interrupted run, `pkill` in the wrong order — Chrome is re-parented to
PID 1 and keeps rendering the board forever.** It does not show in `session list`,
`close --all` will not touch it, and nothing will ever reap it. That is exactly how
a finished run leaves two boards rendering at ~100% CPU and ~2.5 GB (verified: the
leaked instance still carried the run's UA-spoof flags six minutes after the agent
had stopped).

**Always finish a run — successful or not — with this. Both platforms:**

```bash
agent-browser --session miro close 2>/dev/null                 # graceful; no-op if already gone
sleep 2
kill "$(cat ~/.agent-browser/miro.pid 2>/dev/null)" 2>/dev/null  # this session's daemon, if close didn't get it
sleep 2
# whatever is left with parent PID 1 is an orphan — nothing else will ever reap it
ps -Ao pid,ppid,command | grep "[a]gent-browser/browsers/chrome" | grep -v -- "--type=" \
  | awk '$2==1{print $1}' | while read p; do kill "$p"; done
sleep 1
ps -Ao pid,command | grep "[a]gent-browser/browsers/chrome" | grep -v -- "--type=" | wc -l   # must print 0
```

Four details that matter:
- **Order: daemons first, browsers second.** Kill Chrome while its daemon is alive
  and the daemon relaunches it — you end up with a *new* browser plus an orphan.
  `~/.agent-browser/<session>.pid` holds that session's daemon pid (verified).
- **Don't reach for `pkill -f "bin/[a]gent-browser-"` unless you mean it** — it
  kills *every* agent-browser daemon on the machine, including sessions belonging
  to other work. Use it only when the orphan sweep leaves something you can't
  account for, and say so.
- **The `[a]` bracket trick is not decoration** — `pkill -f "agent-browser"` also
  matches the shell running the command, so a plain pattern can kill your own Bash
  call mid-cleanup. The bracket makes the regex not match its own command line.
- **`--type=` filters out Chrome's helper processes** (renderer/GPU/network). One
  instance is ~14-26 processes; count only the ones without `--type=`.

If the count isn't 0, don't leave it — repeat the block, then report what's left.

## Work efficiently (the agent was too noisy last time)

- **Map first, then read each item once** (§3). Most of the flailing in past runs
  was pan-and-peek with no map plus re-reading the same annotation — a single
  overview shot replaces all of it.
- Prefer **text sources over pixels**, and **refs over coordinates** — both cut
  failed attempts.
- **Don't re-open to navigate, and don't ctrl+wheel to zoom** — both produce blank
  screenshots. Stay in the live session; zoom with the +/- buttons.
- **Look cheaply before you shoot:** the ready gate and the zoom-% are text reads
  (≈free); `ls -l` on the PNG is free. Spend a vision token only on an image you
  already know is worth reading.
- **Finish fast, then close.** Every extra turn with the board open is another
  core-minute (§0); every leaked instance doubles it (§5). Efficiency here is a
  resource decision, not just a token one.
- `grep` the `snapshot` output for what you need instead of dumping the whole
  tree every time.
- Don't re-screenshot or re-read an unchanged view. Act, then verify once.

## Reference files
| File | When to read |
|------|--------------|
| [references/extraction-playbook.md](references/extraction-playbook.md) | Full explore→read→summarize method: comments/frames panels, board search, panning, reading mockups, dev-handoff format |
| [references/troubleshooting.md](references/troubleshooting.md) | Stuck on splash, blank/skeleton screenshots, bot detection, blocked CDN, private boards, why keyboard zoom fails, the downscaled-coordinate trap, leaked browsers / machine slowdown / container OOM |
