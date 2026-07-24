# Troubleshooting Miro

**Platform first.** Run `uname -s`. Timings, memory ceilings and failure modes
differ between a macOS desktop (`Darwin`) and a headless Linux container
(`Linux`); every section below flags which numbers are which. The diagnostic
commands are portable — they work on both.

## A) Board stuck on the yellow splash logo
Three distinct causes — tell them apart before changing anything. Triage in one
command after attempting to open:
```bash
agent-browser --session miro eval --stdin <<'EOF'
JSON.stringify({
  canvases: document.querySelectorAll('canvas').length,         // >0 => canvas EXISTS, NOT that it painted
  painted:  document.body.innerText.length > 200,               // true => board actually rendered
  loading:  document.body.className.includes('app-loading'),    // true => still bootstrapping
  webdriver: navigator.webdriver,                               // true => bot detection may stall Miro
  ua: navigator.userAgent.slice(0, 60),                         // must NOT contain "HeadlessChrome"
  resources: performance.getEntriesByType('resource').length,   // stuck ~2 => assets not loading
  signin: !!document.querySelector('a[href*="login"], [class*="signup"]')
})
EOF
```
**`canvases > 0` does not mean the board rendered** — see §G. Read `painted`.

**A1 — Bot detection** (`webdriver:true` or `ua` contains `HeadlessChrome`):
close the session, set a real Chrome UA + disable the automation flag, reopen.
These are launch-time, so the daemon must restart:
```bash
agent-browser --session miro close
export AGENT_BROWSER_USER_AGENT="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
export AGENT_BROWSER_ARGS="--disable-blink-features=AutomationControlled"
agent-browser --session miro open "<board-url>"
```
Verified: with both set, the UA loses `HeadlessChrome` and `navigator.webdriver`
becomes `false`.

**A2 — Blocked CDN / realtime** (`resources` tiny and never grows) — **common on a
locked-down container, rare on a desktop**: Miro needs
three host groups — `miro.com` (app), `mirostatic.com` (the JS-bundle CDN), and
`*.miro.com` (realtime, e.g. `rtmp.miro.com`). If only `miro.com` is reachable,
the bundles never load and the canvas can't render.
```bash
for h in miro.com mirostatic.com rtmp.miro.com; do printf '%s -> ' "$h"; nslookup "$h" >/dev/null 2>&1 && echo OK || echo BLOCKED; done
```
If `mirostatic.com` is blocked: add all three to `AGENT_BROWSER_ALLOWED_DOMAINS`
if you use an allowlist; otherwise run from an environment that can reach the
CDN. Fallback when you truly can't render: extract `og:title` from `miro.com`
and tell the user the live canvas is unreachable and why.

**A3 — Private board** (`signin:true`, or a login / "Request access" page):
the board isn't shared "anyone with the link." Authenticate with a persisted
profile so the password never touches the LLM:
```bash
agent-browser --session miro --profile ./miro-profile open https://miro.com/login   # user logs in once
agent-browser --session miro --profile ./miro-profile open "<board-url>"            # reuses it
```
Don't try to bypass an access wall.

## B) `open` "times out" — expected, not a failure
Miro keeps realtime connections open, so a normal load event never fires;
`open` and `wait --load networkidle` both time out even when the board is fine.
**Poll the ready gate instead** (SKILL.md step 1) — ignore the timeout text. Wrap
the `open` in `timeout 25` so the Bash call returns quickly instead of blocking:
a Bash call that overruns the tool timeout can be killed, and that leaks a browser
(§H).

This applies to **every** `open`, including a re-open to re-center: after any
re-open, re-run the gate — **never a blind `sleep`, and never a bare canvas
count** — or you'll screenshot a blank skeleton while the board is still
rendering. Better still, don't re-open to navigate at all (pan/zoom in-session);
re-opening costs a full cold load (~25s on macOS, 50-60s in a container).

## C) Zoom shortcuts do nothing
Miro's **keyboard zoom shortcuts (`Alt+1`, `Ctrl+=`/`Ctrl+-`, arrow keys) do not
register** through agent-browser on the canvas — pressing them is wasted turns.
Zoom with the on-screen **Zoom in/out / Fit-to-screen buttons by `@ref`**
(snapshot → grep `zoom|fit` → click) — they step predictably and never overshoot.

**Avoid the synthetic ctrl+wheel event** (`WheelEvent` with `ctrlKey:true`): it
jumps ~1.5×/tick and overshoots to 1000-2000% in a couple of ticks, dropping you
into blank canvas. If you land there, read the zoom %
(`snapshot | grep -oE '[0-9]+%' | tail -1`) and use the zoom-out button or **Fit
to screen** (behind the zoom-% menu) to recover.

"Fit to screen" lives behind the zoom-% menu; open the menu, then click it. It
resets to the whole board when you've zoomed into empty space.

## D) Clicks miss their target (the downscaled-coordinate trap)
The screenshot image you **view** is downscaled from the real viewport (e.g.
800px shown vs a 1600px viewport, so ~2×). Coordinates you eyeball off that image
do not map to real pixels, so `mouse move`/click by coordinate lands in the wrong
place.
- **Fix: click by `@ref` from `snapshot`** (or `screenshot --annotate`) — refs
  carry the real geometry, no scaling math.
- If you must use coordinates, multiply by `viewport_width / displayed_image_width`.
  Check the real size: `agent-browser --session miro eval 'innerWidth+"x"+innerHeight+" dpr"+devicePixelRatio'`.

## E) "snapshot shows nothing useful" — only half true
The accessibility tree does **not** contain the mockup art (that's canvas
pixels), but it **does** contain the high-value text: **comments** (Activity
panel), **frame names** (Frames panel), board search, and all app chrome. Use
`snapshot` for those; use screenshots only for the canvas art. Don't dismiss
`snapshot` — on change-request boards it's where the requests actually are.

## F) Screenshots are blank, skeleton, or blurry
**This is the single most common silent failure — you shot too early.** See §G
for the timings and the gate. Diagnose without spending a vision token, at the
`1600 1000` viewport this skill sets:

```bash
ls -l ./miro-shots/*.png    # ~10-11 KB = blank, ~13-15 KB = skeleton (both platforms)
```

If a shot is under ~50 KB, **do not Read it** — re-run the ready gate, wait,
re-shoot. A skeleton screenshot is not "a board with nothing on it"; runs have
read them as real and produced confident output grounded in nothing.

**Size cannot tell you a shot is *ready*, only that it isn't blank.** There is a
half-rendered state where shapes, red ink and handwriting have painted but the
**mockup text is still a blurry smear**, and it is the most dangerous frame on the
board: it reads as a real screenshot, so any UI copy "transcribed" from it is
invented. Its size gives it away in neither direction — measured **74 KB on macOS**
(comfortably over the 50 KB floor) and **~332 KB in the container, larger than that
run's finished 265 KB**. A rendered board is likewise not a fixed size (~130 KB and
~265 KB on two different boards/zooms). The gate excludes the blurry state on both
platforms (`innerText` 111→414 on macOS, 187→413 in the container — that is why the
threshold is 200). Never substitute a file-size check for the gate.

**If the browser process dies right as the board would paint, that's memory, not
Miro.** Container: SwiftShader software rasterization peaks at ~3.4-4 GiB and a
4 GiB cgroup gets OOM-killed at exactly that moment — raise the limit, and make
sure a leaked second instance isn't eating half of it (§H). macOS: it won't OOM
(measured peak ~3.8 GB during load, ~1.3 GB idle), but two instances will make the
machine crawl. Never probe paint with `gl.readPixels()` on the 4096×4096 backing
canvas on either platform — that is what pushed the container over in the first
place.

## G) Why `canvases > 0` is a trap (measured on both platforms)
The `<canvas>` element is created **12s (macOS) to 45s (container) before** Miro
paints into it. Same board, same skill, Chrome for Testing 151 / agent-browser
0.32.3.

**macOS (M2, real GPU — ANGLE Metal):**
```
t=4s   canvas=0  title="Miro"             textLen=4     png= 10 KB  <- nothing yet
t=11s  canvas=3  title="Miro"             textLen=4     png= 13 KB  <- a naive canvas-count gate OPENS HERE
t=15s  canvas=3  title="Vlad Copy - Miro" textLen=16    png= 13 KB  <- title resolves; still a skeleton
t=19s  canvas=3  title="Vlad Copy - Miro" textLen=111   png= 74 KB  <- ink painted, MOCKUP TEXT STILL BLURRY
t=23s  canvas=3  title="Vlad Copy - Miro" textLen=414   png=135 KB  <- BOARD ACTUALLY READABLE
```

**Headless Linux container (SwiftShader software raster) — same shape, ~2× slower:**
```
t=10s  canvas=1  title="Miro"             textLen=4     png= 11 KB  <- naive gate opens here, 45s early
t=21s  canvas=7  title="Vlad Copy - Miro" textLen=16    png= 15 KB
t=40s  canvas=7  title="Vlad Copy - Miro" textLen=187   png=332 KB  <- blurry, and the LARGEST file of the run
t=48s  canvas=7  title="Vlad Copy - Miro" textLen=413   png=265 KB  <- readable
```

So `canvases > 0`, `document.title` **and file size** are all false signals on both
platforms — note the canvas *count* isn't even stable between them (3 vs 7), which
is why the gate tests for a full-size canvas, not a count. The only signal that
tracks readability is Miro's accessibility overview populating:
`innerText.length` going 4 → 16 (skeleton) → ~111-187 (blurry) → ~414 (crisp). The
gate tests `> 200`, which sits in the gap on both platforms — that placement is
deliberate, not arbitrary. It costs nothing.

## H) The machine crawls / RAM is gone / "why are two browsers running?"
**Symptom:** during or after a run the host is starved — on macOS the desktop
becomes sluggish; in a container Chrome gets OOM-killed. `agent-browser session
list` shows one session (or none) and you can't see what's eating it.

**Cause 1 — a leaked (orphaned) browser.** `agent-browser` runs a detached daemon
that owns Chrome. Kill the daemon abnormally and Chrome is re-parented to PID 1 and
keeps rendering the board forever. It is invisible to `session list` and immune to
`close --all`, so nothing will ever reap it. Verified in a real run: two instances,
6 seconds apart — the orphan still carrying the run's UA-spoof flags, the live one
launched without them — together ~2 cores and ~2.5 GB, still going minutes after
the agent had stopped. Things that kill a daemon: a Bash call killed for exceeding
the tool timeout, `pkill` in the wrong order, a crash, an interrupted run.

**Cause 2 — the board itself, still open.** One board = ~100% CPU and ~1.3 GB
*idle*, forever (SKILL.md §0). Nothing is wrong; you just left it open.

**Diagnose (portable, free):**
```bash
ps -Ao pid,ppid,command | grep "[a]gent-browser/browsers/chrome" | grep -v -- "--type=" \
  | awk '{print ($2==1 ? "ORPHAN " : "live   "), $1}'
```
More than one line = more than one browser. `ORPHAN` = `close` cannot reap it.

**Fix:** run the cleanup block in SKILL.md §5 (daemons first, then PPID-1
leftovers, then verify the count is 0). Never `pkill` Chrome before the daemon —
the daemon relaunches it and you end up worse off.

**Prevent:** one session, one command at a time, no parallel Bash calls; keep every
Bash call well under the tool timeout; close the board before you write up.

## I) Misc
- **Cold loads are slow — budget ~25s on macOS, 50-60s in a container; allow ~90s
  / ~180s** before calling it a failure. Poll the ready gate in short repeated Bash
  calls rather than one long one. A `--profile` warms the cache so re-opens are
  faster (it is a launch option, so it must be on the command that starts the
  browser).
- **Blurry screenshot text:** zoom in more before capturing, and/or use a retina
  viewport (`set viewport 1600 1000 2`) for 2× pixel density. **Image-size limit:** a
  screenshot's pixel width is `viewport_width × dpr`; above ~2000px it **fails to
  process** ("an image … could not be processed"). Keep `viewport_width × dpr ≲ 1900`
  — so 1× allows a wide ~1900px viewport (good for reading edge-clipped annotations
  in one shot), but 2× retina needs viewport ≤ ~960 wide. If a shot errors, drop to
  1× or narrow the viewport and re-shoot.
- **`mouse wheel` doesn't pan vertically — it ZOOMS.** Use horizontal wheel
  (`mouse wheel 0 <dx>`) for left/right and a **right-button drag** for up/down
  (left-drag selects a frame). See extraction-playbook.md §5.
- **Re-anchor when lost:** re-open a `?moveToWidget=` link, then re-run
  the ready gate and budget the full cold load. For big multi-screen clusters
  this beats panning across the canvas.
- **Save screenshots in your working dir, not the skill folder.**
- **One session for the whole task** (`--session miro`); `close` it when done.
