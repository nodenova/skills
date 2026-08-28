# Google Ads UI walkthrough (verified Aug 2026)

Step order, and what goes wrong at each step.

## Driving this UI at all

**Use `find` → `ref` for every click.** Coordinate clicking is unreliable here: the screenshot coordinate frame and the page's CSS pixel frame diverge, so a coordinate computed from a scaled screenshot lands on the wrong element — or on nothing, which looks identical to a click that did nothing.

Symptoms of the frame mismatch: clicks that "work" but change nothing, a tooltip appearing somewhere unrelated, an expandable section toggling when you aimed at a menu item below it.

Other standing hazards:

- **Screenshot after every navigation.** This UI re-renders under you.
- **Wait generously.** Ten seconds is often not enough after navigation; the app shows its logo splash then re-renders. `find` can fail with "page still loading" for 30+ seconds.
- **Refs go stale after a re-render.** Re-run `find` rather than reusing a ref across a navigation.
- **Some panel dropdowns don't commit on click.** The campaign conversion-goal selector opens, highlights, then collapses without applying — clicking the option, keyboard Down+Enter, and coordinate clicks all fail the same way. Don't hammer it; tell the user the two manual clicks.
- **macOS: `cmd+a`, not `ctrl+a`** to clear a textarea. `ctrl+a` deletes one character and silently interleaves your content with Google's.
- **`find` returning "not found" is not proof of absence.** It searches the rendered accessibility tree, which may not include collapsed panels or unloaded tables. Navigate to the dedicated page before concluding something doesn't exist.

## URLs that work, and one that doesn't

| Page | Path |
|---|---|
| Campaigns | `/aw/campaigns?ocid=<ID>&authuser=<N>` |
| Ad groups | `/aw/adgroups?campaignId=<ID>&ocid=<ID>` |
| Ads | `/aw/ads?campaignId=<ID>&ocid=<ID>` |
| Keywords | `/aw/keywords?campaignId=<ID>&ocid=<ID>` |
| Negatives | `/aw/keywords/negative?campaignId=<ID>&ocid=<ID>` |
| Locations | `/aw/locations?campaignId=<ID>&ocid=<ID>` |
| Ad schedule | `/aw/adschedule?campaignId=<ID>&ocid=<ID>` |
| Conversions | `/aw/conversions?ocid=<ID>` |
| Account settings | `/aw/settings/account?ocid=<ID>` |

`/aw/keywords/search` and `/aw/campaigns/settings` **404**. Campaign settings has no direct URL — open it from the **Campaign settings** button in the campaign header bar.

The left-nav accordion is unreliable to drive; prefer direct URLs.

## 0. Account state

If `/aw/campaigns` redirects to `/aw/signup/...`, the account is **not activated** and is locked in the guided wizard — no ad groups, no match types, no negatives, no drafts.

**Escape:** business-info step → bottom → **"Not ready for a campaign? Set up an account only"**. Don't try to reach `/aw/overview` directly; it bounces.

Then *Confirm your account settings* — **billing country, time zone, currency are permanent.** Confirm all three with the user before Continue.

Then payment settings → card and Terms. **Hand off to the user.** Expect a "Verify it's you" challenge.

## 1. New campaign

Campaigns → **+ → New campaign**. Never **"Resume campaign draft"** — that resumes stale wizard state, sometimes a leftover Performance Max.

Objective: **"Create a campaign without guidance"**. Type: **Search** — check the radio actually moved; hovering can highlight the wrong card.

## 2. Bidding

"What do you want to focus on?" defaults to **Maximize conversions**. Change to **Clicks** (under *Other optimization options*). Tick **Set a maximum cost per click bid limit**, roughly 60% of daily budget.

## 3. Campaign settings — the money step

Both pre-ticked; untick both:
- **Google Search Partners Network**
- **Google Display Network**

Locations default to **All countries and territories**. Set the target country.

**Location options** (collapsed) default to *"Presence or interest"*. Change to **"Presence"**.

## 4. AI Max

Off by default. Leave it off. Check *Text customization* and *Final URL expansion* are also off.

## 5. Keyword and asset generation

**Skip.** Uses AI-written assets instead of the user's.

## 6. Keywords and ads

Textarea is **pre-filled with generic Google suggestions** — clear it completely, screenshot to confirm empty, then type one per line:

```
"phrase match keyword"
[exact match keyword]
broad match keyword
```

Ads: Google pre-fills 3 headlines and 2 descriptions of its own — overwrite them.

**"+ Headline"** shifts fields down ~71px per addition. Add slots, then re-run `find` for the new empty refs.

Filled description fields sometimes resolve to a `DIV` in the accessibility tree and `form_input` fails. Target the empty-field refs and overwrite in order.

Display path: two 15-char segments. **This is cosmetic ad text, not the destination** — make it represent the real landing page.

## 7. Budget

**Campaign total budget** = true lifetime cap, requires start and end dates. **Average daily** can spend 2× on a day. Type **cannot be changed once the campaign starts**.

Ignore Google's recommended figure — typically 3× a test budget.

## 8. Review

Verify: Networks **Google Search Network** only · Locations · Search term matching **"Using only your keywords and match types"** · budget line.

*"Asset optimization: Text customization and Final URL expansion turned on"* can appear even when AI Max is off. Cross-check the "Search term matching" line — that's the one that governs expansion.

## 9. Stop

**Do not click Publish** without explicit approval. Verify at Campaigns: status **Draft**, "You don't have any enabled campaigns", **Total: Account £0.00/day**. Screenshot it.

A temporary card authorisation (~£10) from verification is **not** ad spend.

## 10. After the campaign exists

Only now possible:

- **Second ad group** — Campaigns → Ad groups → **+**
- **Ad group negatives** — Keywords → Negative keywords tab
- **Shared negative list** — Tools → Shared library → Negative keyword lists → create → attach
- **Conversion tracking** — Goals → Conversions

**The negative keywords panel resets its "Add to" scope to Campaign every time it reopens.** Switch it to Ad group and select the right group on every session.

**After adding an ad group post-publish, verify its keyword count.** The keyword step is easy to lose — the group can end up with its ad and all its negatives and no keywords, and nothing in the campaign view flags it.

## Adding keywords to an existing ad group

Keywords page → blue **+** → **Select an ad group** dialog. The list may render blank; type into the search box to filter, then click the row.

The Add Keywords textarea is **empty** in this flow (unlike campaign creation) — no Google suggestions to clear. Enter with match-type syntax and Save. New keywords show `Under review`; read the second status line for `Low search volume`.

## Editing an ad

Hover the ad row → pencil. The edit button's accessibility label carries `finalUrls: …` — a fast way to read the destination without opening the editor.

Saving re-submits the ad for review. A policy check usually returns within seconds: "Google Ads reviewed the ad that you just saved and found no policy issues."

## Recurring interruptions

- **"Verify it's you"** at account creation and budget save. Stop; the user must complete it. **A half-completed auth leaves the session silently failing writes** — this has caused draft data loss. Wait for full completion before resuming saves.
- **Onboarding coach-marks** intercept clicks. Dismiss via "Exit guide" → Leave.
- **"Changes failed to save"** bottom-left often follows an auth interruption. Reload and re-verify persisted state before trusting the screen.
- **The `claude-in-chrome` extension disconnects after ~4 minutes idle.** Reconnect via the Claude side panel.
