---
name: tender-portal-bidding
description: "Register on public-sector e-procurement portals and complete selection questionnaires, without guessing on a warranted form."
---

# Tender portal registration and selection questionnaires

Public-sector bidding has one structural feature that drives everything else: **the documents that tell you whether you can win are behind a registration wall, and the public notice is a poor summary of them.** The work is therefore: get through the wall cheaply, read what is actually being bought, and only then decide whether to bid.

## The order of operations

1. **Register on the portal** — before deciding anything about the opportunity.
2. **Express interest / accept the invitation** — this is usually what unlocks documents.
3. **Read the specification and the bid pack.**
4. **Then** decide bid/no-bid.
5. Only then start drafting answers.

Deciding at step 0 from the notice text is the most common and most expensive mistake.

## Rule 1 — a notice tells you the subject, not the shape

A notice describes the buyer's *subject matter*. It rarely states the **shape** of the deliverable, and shape decides whether the supplier can bid at all. The four shapes:

| shape | what the buyer actually wants |
|---|---|
| **Build** | bespoke development or a defined technical piece of work |
| **Product licence** | something that already exists, deployed and supported — look for "turnkey", a short go-live date, "onboarding and training" |
| **Accredited service** | work only certified people may perform (e.g. CREST/CHECK security testing) — a certification the supplier *holds* is not the same as accreditation to *perform* |
| **Programme delivery** | recruiting, mentoring or running a cohort; measured on outcomes for participants, not on artefacts |

Expect notices to read more favourably than the brief. Check the buyer's other live tenders on the same portal — they reveal what that buyer habitually purchases.

**Report a shape mismatch plainly, even when it contradicts an existing shortlist.** A user is better served by "this is not what it looked like" than by help writing a losing bid.

## Rule 2 — a submission deadline is not a document-request deadline

Portals frequently close **document requests** days before the stated submission deadline, and that earlier date appears only inside the portal. On registering, record the portal's own date, not the notice's.

## Rule 3 — the bid pack is the authority on thresholds

Notices routinely say only *"selection criteria as stated in the procurement documents"*. The real gates live in the bid pack: financial thresholds, insurance minimums, mandatory certifications, and an explicit list of rejection grounds.

**Questions labelled "(optional)" in a questionnaire can be express rejection grounds in the bid pack.** Always check before treating one as skippable.

A bid pack is often a large archive. Reading it beats downloading it: fetch it same-origin from the portal page and parse the archive in memory rather than pulling megabytes to disk.

## Rule 4 — never put a number or a claim on a warranted form unless it came from a document or from the user

Selection questionnaires carry a declaration that answers are accurate and that evidence will be produced *on request and without delay*. Two failure modes:

- **Marketing copy becoming a warranty.** A website's target-market line ("we serve X, Y and Z sectors") is not a client list. Rewriting it as fact on an SQ is misrepresentation.
- **Plausible figures.** Insurance levels, turnover thresholds and financial minimums are *specified in the bid pack*. "Typical" is not a source, and typical values are often wrong.

When a figure is needed and no source is at hand, go and find the document. If it cannot be found, ask.

## Rule 5 — the human/agent boundary

This split is stable across every portal. State it early so it is not renegotiated at each step.

| Only the user | Can be prepared for them |
|---|---|
| Passwords, CAPTCHAs, emailed one-time codes, 2FA | Every company data field |
| Accepting terms of use and buyer T&Cs | Reading and summarising what is being accepted |
| **Grounds-for-exclusion declarations** — convictions, fraud, corruption, tax compliance | Explaining what each asks; identifying which are objectively "no" and why |
| Statements about an individual's criminal history, ownership share, or date of birth | Public-register facts: names, share bands, nationality, registered addresses |
| Legally-binding declarations and final submission | Every narrative answer, drafted and evidenced |
| Commercial commitments — buying insurance, offering a guarantee | The exact levels required, quoted from the bid pack |

Being useful within the boundary means doing more than declining: explain each question, mark the ones that are objectively answerable from record, and say why. A user clicking seven "No"s should know which needed thought.

## Rule 6 — registration gates on one mailbox

Set-password links, one-time codes, and human-reviewed portal approvals all arrive by email. Whoever holds that inbox is on the critical path for every registration. Say so, and check it is being watched.

Expect these gates: email verification, CAPTCHA, OTP, 2FA setup with a separate PIN, and human review before login details are issued. Portal MFA labels are often misleading — a field called "security code" may want the authenticator digits while a "PIN" is a separate secret set at enrolment.

## Rule 7 — the reference problem for new companies

Questionnaires ask for up to three contracts from the past three years. New companies cannot supply them, and questionnaires usually provide an explicit escape (a short explanation for start-ups). Fill it with what can be **checked**:

1. **Named CVs** of the people who will deliver — individual record where corporate record is absent.
2. **Verifiable artefacts** — repositories, demos, reference implementations that can be inspected rather than believed.
3. **Credentials actually held**, worded precisely. "Certified to X" and "aligned to X" are different claims; conflating them is misrepresentation.
4. **A declared partner** holding the references. Subcontracting is normal, not a weakness — but if used, the bidding-model questions must say so.

Write it as "here is checkable evidence" rather than "here is why we are new".

## Rule 8 — build the answers once

The standard questionnaire is substantially identical across buyers. Keep a dossier holding: legal name, company number, DUNS, registered address, incorporation date, VAT status, SIC and CPV codes, trading status, SME classification, PSC details, contact block, and the standing narrative answers. Record judgement calls (e.g. how the professional-register question was answered) so they are answered identically every time.

For category and classification pickers: **breadth beats tidiness.** A missed alert costs a bid; an irrelevant one costs a keystroke. Take the parent category as well as the children, take the "Other/General" catch-all in any group you belong to, and refuse only categories that would mean bidding for goods you do not sell.

## Verification

Before treating an application as done:

- Every threshold answer traced to a line in the bid pack, not to expectation.
- No claim on the form that cannot be evidenced within a few days.
- Document-request deadlines recorded from the portal, not the notice.
- Declarations, terms and commercial commitments left to the user.
- Bid/no-bid re-checked against the documents, not the notice.