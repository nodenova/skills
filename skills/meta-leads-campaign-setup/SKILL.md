---
name: "meta-leads-campaign-setup"
description: "Set up a Meta (Facebook/Instagram) Leads campaign to a website lead magnet: Pixel + CAPI tracking, Events Manager checks, Ads Manager build via Claude in Chrome, left as a draft."
---

# Meta Leads campaign setup (website conversion)

Use this when the user wants a Meta ads campaign that sends people to a page on their own site (an assessment, a lead magnet, a booking page) and optimises for an on-site event. It covers tracking, account checks and the Ads Manager build.

## Hard rules

- **Never publish.** Do not click "Publish" or "Preview to publish" and do not switch anything on. The campaign stays a draft until the user explicitly says to publish, in chat, for that campaign. Say so when you start.
- **Never enter passwords** (Instagram, Facebook, "Log in with Facebook"). The user signs in; you continue once they say they are in.
- **Consent and terms screens are the user's call.** Example: Instagram's "Use for free with ads / Subscribe" choice applies to every account in the Accounts Center. Show the options, ask, and let the user click it if they prefer.
- **Public profile changes** (profile photo, bio) need a clear yes in chat before you do them.
- Decline optional cookies on consent banners by default.
- Do not ask the user questions whose answer is in the plan files, the code or the account. Look first. Keep questions for genuine decisions.

## 0. Read before touching anything

1. The campaign plan: whatever campaign docs or launch pack the user provides. These usually hold names, budget, audience, copy per ad, headlines, CTA, UTMs, banned claims and creative file names. Build from them verbatim.
2. The website repo, if available. Grep for `fbq(`, the dataset ID, `graph.facebook.com`, `connect.facebook.net`. Note whether the Pixel is consent-gated.
3. Events Manager for the dataset: Overview (set the date range to **today**; the default range ends yesterday and looks empty), Settings, History, Test events.
4. Business settings: Domains (verified?), Ad accounts, Pages, Instagram profiles. Ads Manager Billing (currency, payment method, VAT) and Account Overview.

Report a short done / still-to-do list before building.

## 1. Tracking the campaign needs

Standard mapping for an assessment-style funnel (rename the custom events to fit the funnel):

| Event | When | Type |
|---|---|---|
| PageView | page load (with consent) | standard |
| ViewContent | landing page, `content_name` set | standard |
| `<FunnelStarted>` | first interaction (e.g. first answer) | custom (`trackCustom`) |
| `<FunnelHalf>` | half-way point | custom |
| Lead | successful submit with email | standard, with `eventID` |
| Schedule | confirmed booking | standard |

Code points that matter:
- If the Pixel loads only after marketing consent, `fbq` does not exist on a first visit, so the ViewContent sent on load is lost. Re-send it on the site's consent event.
- Lead needs a shared id: generate `crypto.randomUUID()` in the browser, pass it as `{ eventID }` to `fbq('track','Lead', {}, { eventID })` and send the same id to the server.
- Server CAPI: POST `https://graph.facebook.com/<version>/<pixelId>/events` with `event_name: 'Lead'`, `event_id`, `action_source: 'website'`, `event_source_url`, and `user_data` = sha256 of the lowercased trimmed email, `fbp`, `fbc`, `client_ip_address`, `client_user_agent`. Fire and forget; log success and failure. Send only when the browser reported marketing consent. Keep the Pixel ID and CAPI token in env vars, never in code (token from Events Manager, Settings, Conversions API, Generate access token).
- `fbc` is null on direct visits; it only exists after an ad click with `fbclid`. Not a bug.

## 2. Verifying tracking (the traps)

- **Test Events turns your own browser into test traffic.** With the Test Events tab open, events from the same browser show there but do not count in live stats, and custom events will not appear in custom-conversion dropdowns yet.
- **Server events without `test_event_code` never show in Test Events.** Verify CAPI from the server log (Graph API response `events_received: 1`) or the event's detail panel (`serverProcessedCount`).
- A full test run submits a real lead (emails, alerts, nurture). Agree the test email first and ask the user to delete the test lead after.
- Live stats lag 20 to 30 minutes, longer for a brand-new dataset. Do not sleep-wait in long loops; move on to the Ads Manager build and come back.
- In Test Events the URL may show only the domain (`https://site.tld/`). Custom-conversion **URL rules must therefore use the domain**, not the page path, or they never match. The event itself already scopes to the page.

## 3. Events Manager settings to review with the user

- **Automatic advanced matching**: when on, the Pixel scrapes email and names from form fields (the Lead detail shows "X% receiving Email, First name, Last name"). Conflicts with sites that promise no PII in tracking; CAPI already sends the hashed email. Recommend off; user decides.
- **"Automatically include more detailed page and product info"**: AI page scraping; flag it.
- **Meta-hosted CAPI / Conversions API Gateway** ("Connection pending" or `metaHostedCapiProcessedCount` in event details): a third copy of each event alongside browser + your server. Redundant once server CAPI works; suggest disconnecting.
- Domain verification (Business settings, Brand safety, Domains).
- Custom conversion: Create (top right of the dataset), Create custom conversion, Event = the custom event (appears only after live events), Rule URL contains `<domain>`. Name it after the event.

## 4. Account prerequisites

- Ad account in the right currency with a payment method. VAT number only if the company is VAT-registered.
- Account Overview may say "Account info needed": drafts still save, publishing is blocked until confirmed.
- Facebook Page connected; check followers and posts (a page with a handful of posts looks more credible at launch).
- Instagram profile: ads will not run on Instagram (and Threads, which uses the IG account) until (a) the owner logs in and makes the ads choice, and (b) the profile has a photo. Ad previews show "Advertising currently limited" / "Missing Instagram Profile Photo". A 512px site icon works as a photo.

## 5. Campaign and ad set build (Ads Manager)

Open `adsmanager.facebook.com/adsmanager/manage/campaigns?act=<ad account id>`. Create, Leads.

Campaign:
- Name from the plan (a pattern like `<product> | leads | <country> | <offer> | <yyyy-mm>` keeps reports readable).
- Advantage+ leads campaign stays on; campaign budget (daily) from the plan; bid strategy Highest volume.
- Special ad categories: none unless the product itself is financial/credit/employment/housing.

Ad set (defaults to fix):
- **Conversion location defaults to Instant forms: change to Website.**
- Dataset = the site dataset; Conversion event = the custom event (see section 7).
- Attribution default is 7-day click, 1-day engaged-view, 1-day view; fine.
- Audience: location from the plan. **Under Advantage+ audience the hard minimum age caps at 25**; put the real target age range under Suggest an audience, Age. Languages under Controls. No interest suggestions if the plan says broad.
- Placements Advantage+.

## 6. Ads

First ad through the wizard (Set up creative, Video ad or Image ad):
- The media picker filters by the ad type. A PNG cannot be picked inside a Video ad; that is why "images won't upload". Images belong to an Image ad or the Images tab of a placement group.
- Crop step: select the 4:5 as the main media, then Vertical, Replace, pick the 9:16 (placement asset customisation).
- Text step: primary text (use shift+Enter for line breaks), headline, description, CTA (type the CTA label, e.g. "Learn more", into the CTA dropdown).
- **Creative generation**: leave every AI image unselected.
- **Enhancements**: turn off Text improvements, Enhance CTA, Add details to ad layout, Video touch-ups, Flex media.
- Destination: website URL, then URL parameters (UTM string from the plan with `{{ad.name}}`, `{{adset.name}}`, `{{placement}}`).

Essential enhancements are hidden: in the ad editor click Edit next to "Essential enhancements", scroll to the bottom of Advanced preview, untick **Add video effects**, and for images **Adjust brightness and contrast**; also check the Advantage+ list for **Add overlays** and **Add animation** (Meta turns these on for image ads). "Relevant comments" is harmless. Save.

More ads: ad "...", Duplicate, **untick "Add an image"**, Duplicate. Then:
- Rename.
- Media section has three placement groups: Feeds, Stories/Reels, Right column. For each: hover row, pencil, Continue ("customizations will be removed"), Change, pick the file, Save. **Change all three**, or the copy keeps the old ad's video in one slot (usually Right column).
- Edit primary text / headline by clicking the field at its screen position; ref-based clicks there often open the left nav instead.
- Re-check essential enhancements on every ad; duplicates inherit them, originals built earlier may not have them off.

Expected leftover warning on video ads: "Facebook right column: change the media to an image". Ignore.

## 7. Optimisation event: why the start event, not Lead

Meta needs roughly 50 optimisation events per ad set per week to exit learning. At small daily budgets a niche B2B Lead can cost several times the daily budget, so only a few a week: permanent learning, erratic delivery. Optimise for the earlier, more frequent event (the funnel-start event) and still report Lead and the half-way event. Switch to Lead at roughly 15 to 25+ Leads a week or a bigger budget; try the half-way event first if starts come without completions. In the ad set dropdown pick the **active custom event**, not a just-created custom conversion (inactive until new events arrive); both measure the same thing.

## 8. Browser automation notes (Claude in Chrome)

- Load the chrome tools in one ToolSearch call; work in a new tab; always `tabs_context_mcp` after the user touches tabs.
- Prefer coordinates from a fresh screenshot in the Ads Manager editor. `scroll_to` + ref click sometimes opens the left navigation drawer: press Escape and click empty space.
- `cmd+a` in a field that is not focused selects the whole page; verify focus with a screenshot before typing over text.
- **Uploading files to Meta**: the Upload button creates an `input[type=file]` only when clicked and opens the native picker, which automation cannot drive. To get an input ref: patch `HTMLInputElement.prototype.click` so file inputs are captured into a global and labelled instead of opening the picker, click Upload, `find` the labelled input, `file_upload` one file (inputs are single-file), repeat per file, then restore the original `click` and remove any input appended to `body`. The file must be at a path the upload tool accepts; some environments require staging local files first. Instagram's Edit profile page already has hidden file inputs (label them, then `file_upload`).
- If the user says an upload failed, look at the media library first: often a similarly named variant of the file went up. Search the library by file name.
- Meta modals: "Some customizations will be removed" is expected when editing a placement group; "Adjust brightness may improve performance" needs "Turn off".

## 9. Finish

Report, briefly: what is built (campaign, ad set, each ad with its media and copy), what is still blocking publishing (account info, IG, conversion), tracking status with numbers from Events Manager, and open decisions for the user (advanced matching, Meta-hosted CAPI, test lead cleanup). Do not recap steps.
