# Conversion tracking end to end

Covers wiring, linking, and — the part that consumes the most time — telling a broken chain apart from a working one that merely looks broken.

---

## The chain

A booking has to survive every link to become an attributed conversion:

| # | Link | Verify by |
|---|---|---|
| 1 | Auto-tagging on, so clicks carry a `gclid` | Admin → Account settings → Auto-tagging: Yes |
| 2 | Ad eligible, keyword eligible | ad group view; watch for `Low search volume` |
| 3 | Landing page carries the Google tag **sitewide** | inspect `script[src*=googletagmanager]` on more than the booking page |
| 4 | `gclid` persists as `_gcl_aw` | load the page with `?gclid=test123`, read `document.cookie` |
| 5 | The conversion mechanism exists on the page | the embed or form is actually there |
| 6 | The listener fires `gtag('event','conversion', …)` with the right `send_to` | see "Verifying a listener" below |
| 7 | The Ads conversion action is **Primary** with the right value/window | open the action, read Action optimization |
| 8 | GA4 marks the event as a **key event** | Admin → Data display → Events → star it |
| 9 | GA4 ↔ Google Ads **linked** | Admin → Product links → Google Ads links |

Links 1–7 make the conversion *record*. Link 8 makes GA4 *count* it. Link 9 makes it *diagnosable* — without it you know a conversion happened but not which keyword caused it.

---

## Keep the booking on your own domain

Calendly and similar tools pass UTM parameters through a redirect but **not `gclid`**. Sending traffic to `calendly.com` drops the click ID and produces conversions that can't be traced to any ad.

Embedding the widget on your own domain keeps the `gclid` in the browser. Confirm which architecture is in use before writing any tracking code.

---

## Verifying a listener — what counts

**Doesn't count:** constructing a synthetic event yourself and dispatching it. You choose the event name, the payload shape and the origin, so all you learn is that the handler works when handed a perfect message. It says nothing about what the real widget emits. Reporting this as verification is misleading, and the user will rightly reject it.

**Does count, in ascending order of strength:**

1. **Read the listener source.** Confirm the event name it matches, the origin it validates, and the exact `send_to`, value and currency it passes. Catches typos in the conversion label, which otherwise fail silently for weeks.
2. **Stubbed synthetic dispatch.** Replace `window.gtag` with a recorder, dispatch the event, read what the handler tried to send, restore `gtag`. Nothing reaches Google. Useful for checking parameters — but label it as a wiring check, not proof the widget fires.
3. **A real booking, then the event in GA4.** The only real verification. Check **Admin → Events → Recent events** (includes today) or the Events report with the range set to **Today**.

**Technical note:** `window.postMessage` cannot forge an origin — the browser sets it. A listener that validates `event.origin` will silently ignore a `postMessage` test. `new MessageEvent('message', {origin: '…'})` can set one, which is why a first synthetic attempt often produces nothing. Origin validation is correct security practice, not a bug.

---

## Why working tracking looks broken

Four independent reasons, all encountered in this project.

**1. GA4's default date range excludes today.** "Last 28 days" runs to *yesterday*. An event that fired this morning appears in no default view. The user concludes tracking is broken; it isn't. Always set the range to **Today** when verifying a fresh event.

**2. Realtime only covers 30 minutes.** A booking from earlier today won't be there either.

**3. The event isn't a key event.** GA4 reports zero key events regardless of volume until the event is starred in Admin → Data display → Events. Marking it is not retroactive — events already collected don't become key events.

**4. Google Ads shows "No recent conversions" with no clicks.** No `gclid`, nothing to attribute to, ping discarded. Expected on a paused or non-serving campaign.

The order to check: **Recent events** (does GA4 have it at all?) → **Events report, Today** (how many?) → **key event starred?** → **Ads, and were there clicks?**

---

## Linking GA4 to Google Ads

Easy to skip because the `AW-` tag works without it. Skipping it costs the campaign, ad group and keyword dimensions in GA4, cost data in the Advertising reports, GA4 key-event import into Ads, and audience export.

**GA4 → Admin → Product links → Google Ads links → Link.** Needs GA4 Editor plus Google Ads admin on the same account.

The Configure step has three toggles:

| Toggle | Default | Set to |
|---|---|---|
| **Enable Personalized Advertising** | **ON** | **OFF** unless the user has decided otherwise |
| Enable Auto-Tagging | inherits | leave on |
| Allow access to Analytics features from within Google Ads | ON | fine to leave on |

Personalized Advertising publishes GA4 audience lists and event parameters into Google Ads for ad personalization. That is a user-data decision, not a reporting one — the same category as enhanced conversions. Turn it off, say you did, and note it's one toggle to reverse. Everything the user asked for (reporting, cost, key-event import) works without it.

Data takes **up to 24 hours** to appear, and the link **does not backfill**. Sessions before the link stay uncategorised.

---

## Conversion action settings that matter

| Setting | Sensible default | Why |
|---|---|---|
| Category | the one that describes the action | drives the goal name and grouping; getting it wrong makes reporting misleading |
| Count | **One** | one person booking twice is one lead |
| Value | a nominal figure | lets value-based reporting work later |
| Click-through window | 30–90 days | B2B considers slowly |
| Attribution | Data-driven | fine even at low volume |
| Enhanced conversions | **leave unconfigured** | sends hashed customer emails to Google — a GDPR decision for the user |

Don't import the GA4 key event as a second Ads conversion action while a gtag action exists for the same thing. That double-counts.

---

## Hygiene worth flagging

- **Stray auto-generated conversion actions** ("Submit lead form", "Lead form - Submit") appear from the signup wizard. Set them Secondary so they can't influence bidding.
- **Internal traffic filter.** Test bookings are a material share of a small dataset. Add a filter in GA4 → Admin → Data filters before reading engagement numbers.
- **Data retention** defaults to a short window; raise it if the user will want historical analysis.
