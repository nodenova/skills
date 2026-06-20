# Troubleshooting Miro

## A) Board stuck on the yellow splash logo
Three distinct causes — tell them apart before changing anything. Triage in one
command after attempting to open:
```bash
agent-browser --session miro eval --stdin <<'EOF'
JSON.stringify({
  canvases: document.querySelectorAll('canvas').length,         // >0 => board rendered
  loading:  document.body.className.includes('app-loading'),    // true => still bootstrapping
  webdriver: navigator.webdriver,                               // true => bot detection may stall Miro
  ua: navigator.userAgent.slice(0, 60),                         // must NOT contain "HeadlessChrome"
  resources: performance.getEntriesByType('resource').length,   // stuck ~2 => assets not loading
  signin: !!document.querySelector('a[href*="login"], [class*="signup"]')
})
EOF
```

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

**A2 — Blocked CDN / realtime** (`resources` tiny and never grows): Miro needs
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
**Poll for `<canvas>` instead** (SKILL.md step 1). A non-zero canvas count with
`loading:false` means it rendered — ignore the timeout text.

This applies to **every** `open`, including a re-open to re-center: after any
re-open, re-run the poll — **never a blind `sleep`** — or you'll screenshot a
blank skeleton while the canvas is still rendering. Better still, don't re-open to
navigate at all (pan/zoom in-session); re-opening is a last resort.

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

## F) Misc
- **Cold loads are slow (20-90s).** Use `AGENT_BROWSER_DEFAULT_TIMEOUT=90000`
  and poll. A `--profile` warms the cache so re-opens are faster.
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
- **Re-anchor when lost:** re-open a `?moveToWidget=` link (poll + confirm the
  mockup painted, not gray skeleton). For big multi-screen clusters this beats
  panning across the canvas.
- **Save screenshots in your working dir, not the skill folder.**
- **One session for the whole task** (`--session miro`); `close` it when done.
