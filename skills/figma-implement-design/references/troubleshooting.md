# Troubleshooting Figma (native browser automation)

Fixes for the dead-ends seen when driving Figma via Claude-in-Chrome. Triage the
symptom, then apply.

## A) `javascript_tool` returns `[BLOCKED: Cookie/query string data]`
Your snippet referenced `location`, `document.cookie`, or the query string. The
tool refuses any code that reads those (the URL carries a session token).
- **Fix:** remove `location.*` / `document.cookie` from the code. Use only DOM
  queries (`querySelectorAll`, `innerText`, `getBoundingClientRect`).
- **Need the current `node-id`?** It's printed in the **tab context** after every
  browser action (`…?node-id=3283-121118…`) — read it there, not via JS.
- A `location`-free version of the same extractor always runs fine.

## B) `javascript_tool` returned `{}` / nothing from an async snippet
An `async` IIFE returns a *Promise*, which the REPL prints as `{}` before it
resolves.
- **Fix:** use **top-level `await`** and end with the value/expression:
  ```js
  let out; try { out = await somePromise(); } catch(e){ out = String(e); }
  JSON.stringify(out)
  ```
  Don't wrap in `(async()=>{…})()`.

## C) Clipboard read is denied (`NotAllowedError`)
`navigator.clipboard.readText()` is blocked for the automation, so **"Copy as
SVG" / "Copy as code" can't be read back programmatically** even though the copy
itself succeeds.
- **Icons:** hand-author the inline SVG from a zoomed screenshot, or have the user
  **Export** the node as SVG (downloads a file you can `Read`) — SKILL.md §5.
- **CSS/code:** don't rely on "Copy as code"; read the values from the inspect
  panel (§3) and write the CSS yourself. (It's also usually Dev-Mode-gated.)

## D) The inspect panel extractor returns "NO PANEL"
Nothing is selected, or the right rail is on **Comments** instead of
**Properties**.
- Select a node first (click its **Layers row**, or click/double-click on canvas).
- Make sure the right rail's **Properties** tab is active (top of the rail; the
  other tab is Comments).
- If a node *is* selected and the panel shows values in the screenshot but the
  extractor misses them, widen the climb: the snippet anchors on a section label
  (`Layout`, `Typography`, `Colors`, `Padding`, `Font`) on the right side
  (`left > innerWidth*0.7`) and climbs to a tall container. If Figma changed the
  layout, target the specific value with a text search:
  ```js
  [...document.querySelectorAll('div')]
    .filter(e=>{const o=[...e.childNodes].filter(c=>c.nodeType===3).map(c=>c.textContent).join('');
      return /Fixed \(|Horizontal|px$|#[0-9A-Fa-f]{3,6}/.test(o)&&o.length<40;})
    .map(e=>e.textContent.trim())
  ```

## E) Design-mode inspect vs. paid Dev Mode
A banner "**Get coding, faster … Request access**" means full **Dev Mode** (copy
React/CSS, code connect) needs a **paid Dev seat** this account lacks.
- **Don't wait on it.** The ordinary **design-mode Properties/inspect panel**
  already exposes font/size/leading/tracking/radius/padding/gap/fills/component
  props — everything you need. Proceed with §3 extraction.
- You can dismiss the "Get coding, faster" promo (× on it) to shorten the panel.

## F) File won't open / login or "Request access" wall
- **Login wall:** the user's Chrome isn't signed into Figma. Ask them to open the
  file in their browser and sign in, then retry. Don't attempt to authenticate for
  them (never enter credentials).
- **"Request access":** the link isn't shared to this account. Ask the user to
  share it ("anyone with the link can view") or open a link they have access to.
- **Don't bypass an access wall.**

## G) Canvas never renders (blank / stuck)
Figma is a heavy WebGL SPA; cold loads take a few seconds and the tab title stays
"New Tab" briefly after `navigate`.
- Wait ~4–5s, then poll cheaply:
  ```js
  JSON.stringify({canvas:document.querySelectorAll('canvas').length, title:document.title})
  ```
  `canvas ≥ 1` + real title = rendered. Only then screenshot.
- If it never renders: a blocked CDN/font host, or WebGL disabled. Check the
  network tab / console (`read_console_messages`). If the environment blocks
  Figma's asset hosts, the canvas can't paint — run from an environment that can
  reach them.

## H) Selecting the wrong node — verify before every extraction
This is the #1 time-sink. Two facts from real runs:
- **Canvas selection is the reliable path.** A **single click selects the
  outermost frame** under the cursor; **double-click drills one level deeper**
  each time; `Esc` steps back up. Drill to the node you want.
- **Layers-row clicks frequently mis-hit.** The rows are ~28px tall and the tree
  scrolls, so a click lands on a neighbor or does nothing (seen repeatedly — "the
  layers click missed", "layers-panel clicks aren't registering"). Use the Layers
  panel to **read** the tree as text (SKILL.md §2), not as a reliable click
  target. If you do click a row, treat it as a guess and verify.
- **Always confirm the selected node's name** at the top of the inspect panel (or
  the `node-id` in the tab context) **matches what you meant, before extracting.**
  Extracting from a header-row/text-block instead of its card is a silent error —
  the specs look plausible but belong to the wrong node.
- If you overshoot while drilling, `Esc` up a level or re-click the parent frame;
  don't keep double-clicking blindly.

## I) Framing / zoom
- **`Shift+2`** = zoom to *selection* (frames the selected node). Use it to make a
  node/screen big before a screenshot. **`Shift+1`** = fit **all** page content —
  on a multi-frame file that can be ~2% and useless, so prefer select + `Shift+2`,
  or re-`navigate` with the target `?node-id=`.
- **The `zoom` screenshot action (region capture) is unreliable here** — its
  coordinates drift and it misses small targets (icons, tiny labels). Instead
  **zoom the Figma canvas itself** (`Shift+2` on the element) so it renders large,
  then take a normal `screenshot`.
- The top-right **zoom %** dropdown also has "Zoom to fit / 100%".
- If a node is bigger than the viewport even zoomed-to-fit, screenshot in
  overlapping tiles, or widen the browser window.

## J) Coordinates
- Screenshot pixels map ~1:1 to click coordinates (the tool accounts for the
  device-pixel ratio, ~1.8 here), so clicking canvas elements by eye from the
  latest screenshot works — this is the workhorse for selection (§H).

## K) Hygiene
- **Two tabs:** the Figma file and the running app, for the compare loop. Within
  the Figma tab, `navigate` once then select/zoom/screenshot in-session;
  re-navigating to a different `?node-id=` reloads the whole SPA (slow) but is a
  fine way to jump to a distant frame when drilling gets lost.
- **Save screenshots in the project/working dir**, not the skill folder.
- **Close the tab** when done (`tabs_close_mcp`) unless the user wants it open.
