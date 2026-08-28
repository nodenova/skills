---
name: google-search-campaign
description: Build, launch, audit and verify a Google Ads Search campaign from a spreadsheet of headlines, descriptions, keywords and negatives — checking demand exists before building, validating assets against Google's limits, wiring conversion tracking end to end, and driving the browser UI without tripping its defaults. Use when setting up or launching Google Ads, importing ad copy from a sheet, running a small paid demand test, auditing an account, diagnosing a campaign that isn't serving or spending, or when conversions aren't showing up in Google Ads or GA4. Triggers include "set up google ads", "launch ads", "run a paid test", "audit my google ads", "why is my campaign not spending", "why are there no impressions", "my conversions aren't tracking", or a supplied .ods/.xlsx/.csv of ad assets.
license: Proprietary
---

# Google Ads Search campaign builder

Build validated, budget-safe Search campaigns and verify they actually work. Default posture: **nothing goes live without explicit approval**, and **no state is reported without reading the underlying object**.

## Operating rules

1. **Never publish or enable a campaign without the user saying so in this conversation.** Build to draft or paused.
2. **Never enter payment details, card numbers, or passwords**, and never accept Terms on the user's behalf. Hand re-auth challenges to the user and wait.
3. **Never make a privacy decision on the user's behalf.** Enhanced conversions, Personalized Advertising, and Customer Match all share user data with Google. Default them **off**, say you did, and let the user turn them on.
4. **Ask before assuming** budget, geography, bidding, match types, or launch order.
5. **Report every change you made to their source data.**
6. **Read the object, not the label.** See below — this is the rule that gets broken.

## The label trap

Google Ads surfaces summary labels that look like settings but aren't. Reading them as settings produces confident, wrong diagnoses. In this project it happened twice.

| The label says | What it actually is | Read this instead |
|---|---|---|
| Ads table shows `site.com/foo/bar` | **Display path** (Path 1 / Path 2) — cosmetic ad text | Open the ad → **Final URL** field |
| Conversion goal: "Submit lead forms" | A **goal category** that may contain several actions | Goals → **View all conversion actions** → open the action → **Action optimization** |
| Goals summary shows one goal group | Only shows *primary* goals, grouped by category | The conversion actions table, `Status: All enabled` |
| "No recent conversions" | No *attributable* conversion yet | Expected with zero clicks — Ads discards pings with no `gclid` |
| Keyword "Under review" | New keyword, normal | Look for the second line: `Low search volume` is the real status |

Before reporting any configuration as wrong, open the underlying entity and read its own fields. A wrong diagnosis costs more than the check.

## Phase 0 — Check demand exists before building

**Do this first.** It is free, takes minutes, and can invalidate the whole plan.

Niche B2B vocabularies frequently have too little volume to serve at all. In this project **13 of 24 keywords** came back `Not eligible — Low search volume` — 3 of 13 in one ad group, 10 of 11 in the other. The campaign served **1 impression in 6 live days on a £50 budget**.

Run the sheet's keywords through **Tools → Planning → Keyword Planner → Get search volume and forecasts** before building anything. Then tell the user plainly:

- Terms with no volume will be loaded but **never serve**. They aren't expensive; nobody types them.
- If most of a group is empty, paid search is the wrong channel for that vocabulary — demand has to be *created* (Demand Gen, lead magnets, outbound), not captured.
- Offer to proceed anyway if they want the empirical answer. Getting it for £0 is a real result, but they should choose it knowingly rather than discover it after the flight ends.

Low search volume can lift later if query volume appears, so these keywords are dormant rather than dead.

## Phase 1 — Read and validate the spreadsheet

Parse every sheet before touching a browser. Columns are usually: ICP · headlines · descriptions · keywords · per-group negatives · shared negatives. Groups stack vertically in one sheet with launch-order notes **sometimes in another language** — read the whole grid cell by cell, and translate marginal notes. A group marked "don't include yet" in Ukrainian is still an instruction.

Validate against these limits with a script, never by eye:

| Rule | Limit |
|---|---|
| Headline length | 30 chars |
| Description length | 90 chars |
| Headlines per ad | 3–15, no exact duplicates |
| Descriptions per ad | 2–4, no exact duplicates |
| Negative vs own keyword | no negative may block an own keyword |

Run `references/validate_assets.py` if bundled; it implements the conflict check and exits non-zero on failure. Reimplement inline if absent (~20 lines).

**Conflict rules:** broad negative blocks if *every* token appears in the keyword (broad `audit` kills `coverholder audit`); phrase negative blocks a contiguous substring; exact blocks only an identical keyword.

Report every fix as a table. Findings that recur:

- **Misspellings** (`insuranse`) — serve nothing, silently. Fix and flag.
- **Over-limit headlines** — rejected at upload. Shorten deliberately, don't truncate silently.
- **Duplicate headlines in one ad** — rejected. Deduplicate and say which you dropped.
- **A fifth description** — max is 4. Name the one you left out so the user can swap.
- **Near-duplicate keywords** (`ai governance insurance` / `insurance ai governance`) — distinct as phrase match, functionally overlapping. Drop one.
- **A keyword with no qualifier** (`algorithmic decision audit`) — will pull unrelated traffic your negatives don't cover.
- **A negative that blocks a keyword** — the most damaging and least visible error.

## Phase 2 — Decide the structure

Ask, don't assume:

- **Which ad groups launch now.** Sharply different vocabularies belong in separate campaigns or phases; mixing muddies the read.
- **Budget shape.** For a fixed-spend test prefer **Campaign total budget** (a true lifetime cap) over average daily (can spend 2× on a day). Campaign total **requires start and end dates**, and the type **cannot be changed after the campaign starts**.
- **Geography.** Narrow beats broad on small budgets.
- **Match types.** Sheet conventions: `[x]` exact, `"x"` phrase, bare broad. Under ~£200 default bare terms to **Phrase**, and say so — broad leaks faster than negatives can catch.
- **Bidding.** With no conversion history, **Maximise clicks** with a max CPC cap around 60% of daily budget. Maximise conversions needs data the account lacks.

## Phase 3 — Build in the browser

Load Chrome tools in one `ToolSearch` call, then `tabs_context_mcp`, and work in a fresh tab.

**Use `find` → `ref` for every click.** Coordinate clicks are unreliable: the screenshot coordinate frame and the page's CSS pixel frame diverge, so a click computed off a scaled screenshot lands somewhere else. Screenshot after every navigation; this UI re-renders under you.

`references/ui_walkthrough.md` has the verified click-by-click, the defaults that cost money, and the UI hazards. Read it before building.

Two things worth stating up front so the user isn't surprised:

- **Negatives cannot be added during campaign creation.** They come after the campaign exists.
- **The creation wizard supports one ad group only.** Additional groups are added post-publish.

## Phase 4 — Verify by reading state back

Never report from the screen you just typed into. Re-navigate and read the saved state.

**After adding an ad group post-publish, verify its keyword count specifically.** In this project a second ad group was created with its ad and all 14 of its negatives, but **zero positive keywords** — and it sat that way through launch, serving nothing. Campaign-level totals hid it because the first group's keywords made the number look plausible. Check per ad group, not per campaign.

Full audit checklist in `references/verification.md`. Run it before launch and again whenever the user asks whether something is set up properly.

## Phase 5 — Conversion tracking

Set this up before spend, verify it after. `references/conversion-tracking.md` covers the full chain, the GA4 ↔ Google Ads link, and the reporting traps that make working tracking look broken.

Three things that were missed or misjudged in this project and are worth pre-empting:

1. **Link GA4 to Google Ads.** Easy to overlook because the `AW-` conversion tag works without it. Without the link, GA4 cannot show campaign, ad group or keyword for any session — which is exactly the diagnosis a demand test needs. The link wizard defaults **Enable Personalized Advertising to ON**; turn it off unless the user has decided otherwise.
2. **GA4's default date range excludes today.** "Last 28 days" ends *yesterday*. A conversion that fired this morning is invisible in every default view. Check **Today**, or Admin → Events → **Recent events**, which does include today.
3. **A forged event does not verify a listener.** Dispatching a synthetic message you constructed yourself only proves the handler works when handed a perfect message. It proves nothing about what the real widget emits. See the reference file for what does count as verification.

## Phase 6 — Deliverables

1. A **status document**: what's built, what's outstanding, every change to the source sheet, and judgement calls to review.
2. **Google Ads Editor CSVs** as an executable backup — see `references/editor_csv_format.md`. Generate even when building in the UI; they survive session loss. `Campaign Status` always `Paused`.
3. An **ad preview** for approval before spend — see `references/ad_preview_template.html`.

## Interpreting a small-budget test

At £50 with B2B CPCs of £3–8, expect **15–25 clicks** — far too few for conversion-rate conclusions. Say this before launch.

The deliverable is the **search terms report**: which real queries triggered the ads. If the campaign barely served, the deliverable is instead the **keyword eligibility report** — which terms Google marked low-volume. Both answer the real question, which is where demand lives.

Ad strength "Average" is fine. Google rewards generic keyword-stuffed headlines; ICP-specific copy scores lower and speaks to the right buyer. Don't chase "Excellent" at the cost of specificity. "Pending" just means not yet calculated.

## Advice worth giving unprompted

- **Performance Max is wrong for a validation test.** No keywords, no match types, no campaign-level negatives, hides which channel spent, and needs conversion history. Search first.
- **Display/YouTube presence is legitimate but not via the Display checkbox** on a Search campaign. Separate Demand Gen campaign with its own budget.
- **Decline the Google account strategist** on small test accounts. Reps are measured on spend; standard advice is more budget and PMax.
- **A campaign total budget spread over more days thins daily pacing.** Extending an end date is usually right when nothing has spent, but flag the trade-off if delivery picks up.
- **Own test traffic pollutes small datasets.** Four test bookings against twenty users is a material share. Recommend a GA4 internal traffic filter before reading engagement numbers.

## Reference files

- `references/verification.md` — the pre-launch and audit checklist, and how to read each object rather than its label
- `references/conversion-tracking.md` — the measurement chain end to end, GA4 ↔ Ads linking, and why working tracking can look broken
- `references/ui_walkthrough.md` — verified click-by-click, money-costing defaults, UI hazards
- `references/editor_csv_format.md` — Google Ads Editor import spec
- `references/validate_assets.py` — asset and negative-conflict validator
- `references/ad_preview_template.html` — self-contained ad preview for user approval
