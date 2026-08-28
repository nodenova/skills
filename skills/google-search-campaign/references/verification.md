# Verification and audit

Use this before launch, and whenever the user asks whether something is set up properly.

The governing rule: **open the entity and read its own fields.** Summary rows, goal names and display paths are labels *about* objects, not the objects. Every wrong diagnosis in this project came from reading a label.

---

## 1. Read the object, not the label

### Final URL vs display path

The ads table shows a **display URL**: the Final URL's domain plus Path 1 and Path 2. Path 1/2 are free text, capped at 15 characters each, and have no connection to where the click goes.

An ads table reading `site.com/authority-gap/assessment` is entirely compatible with a Final URL of `https://site.com/products/remit`.

- **To read the destination:** hover the ad row → pencil → **Final URL** field. The edit button's accessibility label also carries `finalUrls: …`, which is a fast read via `find`.
- **To check the display path is honest:** Google requires the display URL to represent the landing page. A path pointing at a route that doesn't exist is a policy risk and should be corrected — but it is an ad-copy edit, so confirm before changing, and expect both ads to re-enter review.

### Conversion goals are categories, not actions

The campaign setting **Conversion goals** lists *goal categories* (Submit lead forms, Book appointments, Purchases…). Each category contains one or more conversion actions. Only actions marked **Primary** count as conversions and influence bidding.

So a campaign whose goal reads "Submit lead forms" may in fact be optimising toward a Calendly booking — if that action was created with the *Submit lead form* category and is the only Primary action in it.

**To read it properly:** Goals → Conversions → Summary → **View all conversion actions** (the Goals tab alone shows only goal groups and will make an existing action look absent). Then open the action and read:

| Field | What it tells you |
|---|---|
| Action optimization | `<category>, Primary action` or `Secondary` |
| Value / Count / windows | whether it will record what you expect |
| Source | Website vs Google hosted |
| Tracking status | Inactive / No recent conversions / Recording |

If the category is wrong, the fix is editing the action's category — not switching the campaign goal. Changing the category moves the action into the correctly-named goal and makes the campaign dropdown offer it.

### "No recent conversions" is usually correct

Google Ads records a conversion only when it can attribute it to an ad click via a `gclid`. With zero clicks, conversion pings arrive with nothing to attach to and are discarded. This is expected on a paused or non-serving campaign — not a tracking fault. GA4 will still count the event, because GA4 doesn't need a click.

### Keyword status has two lines

`Under review` on a new keyword is routine. The line beneath it is the real status. `Not eligible / Low search volume` means Google will not serve it at all.

---

## 2. Pre-launch checklist

Read each from its own page, not from the review screen.

**Account** — Admin → Account settings

| Check | Correct |
|---|---|
| Account status | Active |
| **Auto-tagging** | **Yes** — precondition for all conversion attribution |
| Time zone | matches the market (permanent) |
| Auto-apply recommendations | Off |
| Data protection contacts | filled in for EU/UK advertisers |

**Campaign** — Campaign settings

| Check | Correct |
|---|---|
| Networks | Google Search Network only |
| Locations | target country; check **Location exclusions** too |
| Location option | Presence, not "presence or interest" |
| Languages | as intended |
| Budget | type and figure; total budgets need an end date |
| **End date** | far enough out that the flight can actually run |
| Bidding | Maximise clicks + CPC cap, with no conversion history |
| Broad match keywords | Off |
| AI Max | Off |
| Automatically created assets | Off |
| Conversion goals | the *action inside* the category is the right one |

**Ad schedule** — should read "Your ads are eligible to show all the time" unless deliberately restricted. A stray schedule is an invisible delivery cap.

**Ad groups** — for each group, separately:

| Check | Correct |
|---|---|
| Status | Enabled |
| **Keyword count** | matches the sheet **per group** |
| Keyword statuses | note every `Low search volume` |
| Ad status | Eligible |
| Final URL | the real destination |
| Display path | represents that destination |
| Negatives | present at the right scope |

The per-group keyword count is the one that gets missed. A group can carry its ad and all its negatives and still have zero keywords.

**Landing page**

- Loads, and is the page the ad promises
- Carries the Google tag sitewide, not only on the booking page
- Contains the conversion mechanism itself (form, embed, button)

---

## 3. Diagnosing "not serving / not spending"

Work down in order; stop at the first that fails.

1. **Campaign end date passed?** A campaign total budget requires an end date and stops dead at it.
2. **Campaign / ad group / ad status** — all Enabled and Eligible?
3. **Keyword count per ad group** — is any group empty?
4. **Keyword statuses** — how many are `Low search volume`? If most, that's the answer, and it's a market finding, not a fault.
5. **Ad schedule** — restricted?
6. **Location exclusions** — anything blocking the target?
7. **Billing** — account active, payment method valid?
8. **Bid cap vs market CPC** — a cap far below first-page estimates suppresses delivery.

Budget is rarely the cause when spend is exactly £0.00 — that pattern points to eligibility, not pacing.

---

## 4. Reporting honestly

- Quote the field you read and where you read it, so the user can check.
- Distinguish "I verified this" from "the summary says this".
- If you previously reported something and later find it wrong, say so plainly, name the specific misreading, and correct the record. Do not bury the correction in a list of successes.
- Separate **fault** from **finding**. Zero conversions because nobody clicked is a finding. Zero conversions because the tag is missing is a fault. Conflating them wastes the user's time on a fix that isn't needed.
