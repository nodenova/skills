---
name: google-search-campaign
description: Build a Google Ads Search campaign from a spreadsheet of headlines, descriptions, keywords and negatives — validating assets against Google's limits, structuring ad groups, and driving the browser UI without tripping its defaults. Use when setting up, launching, reviewing or auditing Google Ads, importing ad copy from a sheet, or testing demand for a product with a small paid budget.
when_to_use: Trigger on "set up google ads", "create a search campaign", "launch ads", "run a paid test", "validate my ad copy", "import ads from spreadsheet", "why is my campaign spending so fast", "audit my google ads settings", or when the user supplies an ads spreadsheet (.ods/.xlsx/.csv) of headlines, descriptions, keywords or negative keywords.
---

# Google Ads Search campaign builder

Build validated, budget-safe Search campaigns from a spreadsheet. Default posture: **nothing goes live without explicit approval**.

## Operating rules

1. **Never publish or enable a campaign without the user saying so in this conversation.** Build to draft or paused; stop at the review screen.
2. **Never enter payment details, card numbers, or passwords**, and never accept Terms on the user's behalf. Google throws re-auth challenges mid-flow — hand those to the user and wait.
3. **Ask before assuming** budget, geography, bidding, match types, or which ad groups launch first. These change the result and are cheap to ask.
4. **Report what you changed in their source data.** Typos and over-limit assets get fixed, but the user must know.

## Phase 1 — Read and validate the spreadsheet

Parse every sheet before touching a browser. Columns are usually: ICP · headlines · descriptions · keywords · per-group negatives · shared negatives. Groups are often stacked vertically in one sheet with launch-order notes (sometimes in another language) — read the whole grid by cell, not by header.

Validate against these limits — write a throwaway script, never eyeball it:

| Rule | Limit |
|---|---|
| Headline length | 30 chars |
| Description length | 90 chars |
| Headlines per ad | 3–15, no exact duplicates |
| Descriptions per ad | 2–4, no exact duplicates |
| Negative vs keyword conflict | no negative may block an own keyword |

**The conflict check matters most and is invisible by eye.** For every negative against every one of your own keywords:

- **Broad negative** blocks if *every* token of the negative appears in the keyword. So broad `audit` kills `coverholder audit`.
- **Phrase negative** blocks if the negative appears as a contiguous substring.
- **Exact negative** blocks only an identical keyword.

If `references/validate_assets.py` is bundled, run it — it implements exactly this and exits non-zero on failure. If the skill was installed as a single file, reimplement the check inline; it's ~20 lines.

Then report every fix as a table: the issue, and what you did. Common real-world findings:

- **Misspelled keywords** (`insuranse`) — near-zero impressions, silently. Fix and flag.
- **Over-limit headlines** — rejected at upload. Drop or shorten, don't silently truncate.
- **Duplicate headlines within one ad** — rejected. Deduplicate.
- **More than 4 descriptions** — pick 4, name the spare so the user can swap.
- **A negative that blocks a keyword** — the most damaging and least visible error.

## Phase 2 — Decide the structure

Ask the user, don't assume:

- **Which ad groups launch now.** Sheets often mark launch order. Vocabularies that differ sharply belong in separate campaigns or later phases — mixing them muddies the read.
- **Budget and shape.** For a validation test, prefer **Campaign total budget** (a true lifetime cap) over average daily budget, which can overspend 2× on any day. Campaign total requires start and end dates.
- **Geography.** Narrow beats broad on small budgets.
- **Match types** for unbracketed keywords. Sheet conventions: `[x]` = exact, `"x"` = phrase, bare = broad. On budgets under ~£200, default bare terms to **Phrase, not Broad**, and say so — broad match leaks into irrelevant queries faster than negatives can catch it. Broad discovers unexpected language; phrase protects the budget. Name the trade-off.
- **Bidding.** With no conversion history, **Maximise clicks** is the only honest choice; Maximise conversions needs data the account lacks. Set a max CPC cap around 60% of the daily budget so one click can't consume a day.

## Phase 3 — Build in the browser

Load Chrome tools in one `ToolSearch` call. Then `tabs_context_mcp`, and work in a fresh tab. Screenshot after every navigation — this UI re-renders under you and coordinate clicks land on the wrong element.

If `references/ui_walkthrough.md` is bundled, read it — it has the verified click-by-click with the exact controls and where each hides. Everything below is sufficient without it.

### Account state comes first

Check whether the account is activated. A **brand-new account is trapped in Google's guided ("Smart") signup wizard**, which cannot create ad groups, match types, negative keywords, or drafts — it only walks to a payment form. Escape it via **"Set up an account only"** at the bottom of the business-info step, not by URL-hacking.

Account creation asks for **billing country, time zone, and currency — all permanent**. Always confirm these with the user before clicking Continue.

### The defaults that cost money

Uncheck or verify these every time. Google pre-selects the expensive option:

| Setting | Google's default | Set to |
|---|---|---|
| Google Search Partners | ✅ on | **off** |
| Google Display Network | ✅ on | **off** |
| Location targeting | All countries | the target country |
| Location option | "Presence **or interest**" | **"Presence"** only |
| AI Max / text customisation / final URL expansion | varies | **off** for a controlled test |
| Bidding | Maximize conversions | **Clicks** + CPC cap |
| Suggested budget | inflated (often 3× your plan) | your figure |

### UI hazards

- **The onboarding coach-mark overlay intercepts clicks.** If a modal keeps stealing input, dismiss the guide itself ("Exit guide" → Leave). This exits the tour, not campaign creation.
- **Never click "Resume campaign draft"** if a stale Performance Max draft exists — it carries wizard state. Always start "New campaign".
- **Reaching the billing page by direct URL can attach a leftover PMax campaign.** If the stepper shows "Your ad ✓ / Budget and review ✓", back out and re-enter via the account-only route, or submitting launches a campaign the user never chose.
- **On macOS use `cmd+a`, not `ctrl+a`**, to clear textareas. `ctrl+a` silently deletes a single character instead.
- **Google pre-fills generic keywords and AI-written ad copy.** Clear both fully before entering the user's assets, then re-screenshot to confirm nothing interleaved.
- Prefer `find` → `form_input` over click-and-type for ad fields; it's far more reliable than coordinate clicking.
- Expect **re-authentication challenges** at account creation and at budget save. Stop, tell the user exactly what to click, wait.

### Negative keywords

Negatives **cannot be added during campaign creation**. Add them after the campaign exists:
- ad-group negatives → the ad group's keyword view
- shared list → Tools → Shared library → Negative keyword lists, then attach to the campaign

Say this up front so the user isn't surprised the campaign looks incomplete.

## Phase 4 — Verify, then stop

Confirm with evidence, not assertion. Screenshot the campaigns table showing:
- status **Draft** or **Paused**
- "You don't have any enabled campaigns"
- **Total: Account £0.00/day**

A draft has never entered the ad auction and has no billing hook. Note that a temporary card authorisation (~£10) from account verification is **not** ad spend.

Warn if the start date is today: publishing serves immediately. Offer to set status Paused at publish so the campaign is fully inspectable while spending nothing.

Delete stray drafts (especially leftover Performance Max) — one misclick from being the thing that goes live.

## Phase 5 — Deliverables

Always leave behind:

1. A **status document** listing what's built, what's outstanding, every change made to the source sheet, and the judgement calls to review.

2. **Google Ads Editor CSVs** as the executable backup. Generate these even when building in the UI; they make rebuilds trivial and survive session loss. Three files: campaign/ad-groups/keywords/ads in one; ad-group negatives; shared negative list. Encode `utf-8-sig`, set `Campaign Status` to `Paused`, keep match types in the `Criterion Type` column (`Broad`/`Phrase`/`Exact`, prefixed `Negative ` for negatives) and out of the keyword text. Full column spec in `references/editor_csv_format.md` if bundled.

3. An **ad preview** the user can approve before spend — a self-contained HTML page rendering each ad as a Google result, with headline combinations shuffling the way Google rotates them, plus per-asset character counts. `references/ad_preview_template.html` if bundled.

## Interpreting a small-budget test

Set expectations before launch. At £50 with B2B CPCs of £3–8, expect **15–25 clicks total** — far too few for conversion-rate conclusions. The deliverable is the **search terms report**: which real queries triggered the ads. That answers which vocabulary demand actually lives in, which is usually the real hypothesis.

Ad strength "Average" is fine and often correct. Google rewards generic, keyword-stuffed headlines; ICP-specific copy scores lower and speaks to the right buyer. Don't chase "Excellent" at the cost of specificity.

## Advice worth giving unprompted

- **Performance Max is the wrong tool for a validation test.** No keywords, no match types, no campaign-level negatives, and it hides which channel spent. It needs conversion history to optimise toward. Recommend Search first, PMax later as a scaling play.
- **Wanting YouTube/Display presence is legitimate — but not via the Display checkbox** on a Search campaign. That mixes the data and eats a small budget on cheap placements. Use a separate Demand Gen campaign with its own budget (needs 1200×628 and 1200×1200 images, ideally video).
- **Decline the Google account strategist** on small test accounts. Reps are measured on account spend; their standard advice is more budget and Performance Max.
- **Conversion tracking absent** means clicks but no enquiries attributed. Flag it early — it's cheap before launch and painful after.
