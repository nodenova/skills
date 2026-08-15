# Google Ads UI walkthrough (verified Aug 2026)

Step order, and what goes wrong at each step. Screenshot after every navigation — this UI re-renders under you and coordinate clicks land on the wrong element.

## 0. Account state

`ads.google.com/aw/campaigns?ocid=<ID>&authuser=<N>`

If it redirects to `/aw/signup/...`, the account is **not activated** and is locked in the guided wizard. That wizard has no ad groups, no match types, no negatives, and no drafts.

**Escape:** business-info step → scroll to the bottom → **"Not ready for a campaign? Set up an account only"**. Do not try to reach `/aw/overview` directly; it bounces.

Then: *Confirm your account settings* — **billing country, time zone, currency are permanent.** Confirm all three with the user before Continue.

Then: *payment settings* → requires a card and Terms acceptance. **Hand off to the user.** Expect a "Verify it's you" challenge.

## 1. New campaign

Campaigns → **+ → New campaign**. Never **"Resume campaign draft"** — that resumes stale wizard state.

Business info: name + final URL → Next.

Objective: **"Create a campaign without guidance"** — avoids Google steering to conversion bidding the account can't support.

Type: **Search**. (Check the radio actually moved; hovering can highlight the wrong card.)

Campaign name, conversion goals, "results you want" checkboxes — leave the result checkboxes unticked with no conversion tracking.

## 2. Bidding

"What do you want to focus on?" defaults to **Maximize conversions**. Change to **Clicks** (under *Other optimization options*).

Tick **Set a maximum cost per click bid limit**. Roughly 60% of daily budget: one click shouldn't eat a day.

## 3. Campaign settings — the money step

Both pre-ticked; untick both:
- **Google Search Partners Network**
- **Google Display Network**

Google immediately offers "Opt in to Search Partner Network / Use Display Expansion" — ignore.

Locations: defaults to **All countries and territories**. Set the target country.

**Location options** (collapsed): defaults to *"Presence or interest"*. Change to **"Presence: People in or regularly in your included locations"**. Interest-targeting pulls overseas searchers onto a small budget.

Languages: usually correct.

## 4. AI Max

Off by default. **Leave it off** for a controlled test — it broad-matches beyond your keywords and rewrites ad text. Check *Text customization* and *Final URL expansion* are also off.

## 5. Keyword and asset generation

**Skip.** Uses AI-written assets instead of the user's.

## 6. Keywords and ads

Textarea is **pre-filled with generic Google suggestions** — clear it completely first.

**macOS: `cmd+a` then Delete.** `ctrl+a` deletes a single character and silently interleaves your keywords with Google's.

Screenshot after clearing to confirm it's empty, then type keywords one per line with match-type syntax:

```
"phrase match keyword"
[exact match keyword]
broad match keyword
```

Ads: Google pre-fills 3 headlines and 2 descriptions of its own copy — overwrite them.

Use `find` to get element refs, then `form_input`. Far more reliable than click-and-type.

**"+ Headline"** shifts down ~71px per added field. Add slots, then re-run `find` for the new empty refs rather than guessing coordinates.

Some filled description fields resolve to a `DIV` in the accessibility tree — `form_input` fails. Target the empty-field refs (which are real textareas) and overwrite in order.

Display path: two 15-char segments.

Click **Done** to commit the ad.

## 7. Budget

**Campaign total budget** = true lifetime cap. Requires start and end dates. Prefer it for fixed-spend tests.
**Average daily budget** can spend 2× on any given day.

Budget type **cannot be changed once the campaign starts**.

Ignore Google's recommended figure — it's typically 3× a test budget.

## 8. Review

Verify on the review screen:
- Networks: **Google Search Network** only
- Locations: the target country
- Search term matching: **"Using only your keywords and match types"**
- Budget line matches intent

⚠️ *"Asset optimization: Text customization and Final URL expansion turned on"* can appear even when AI Max is off. Cross-check the "Search term matching" line — that's the one that governs keyword expansion.

## 9. Stop

**Do not click Publish** without explicit approval. Leaving at review keeps the campaign as a draft.

Verify at Campaigns: status **Draft**, "You don't have any enabled campaigns", **Total: Account £0.00/day**. Screenshot it.

## 10. After the campaign exists

Only now possible:
- **Ad group negatives** — ad group → Keywords → Negative keywords
- **Shared negative list** — Tools → Shared library → Negative keyword lists → create → attach
- **Second ad group**
- **Conversion tracking** — Goals → Conversions

## Recurring interruptions

- **"Verify it's you"** at account creation and budget save. Stop; the user must complete it.
- **Onboarding coach-marks** intercept clicks. Dismiss via "Exit guide" → Leave (exits the tour, not the campaign).
- **"Changes failed to save"** bottom-left often follows an auth interruption. Reload and re-verify persisted state before trusting the screen.
