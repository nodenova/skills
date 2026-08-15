#!/usr/bin/env python3
"""
Validate Google Ads Search assets before upload.

Catches the failure modes that are silent or rejected at upload:
  - headlines over 30 chars / descriptions over 90
  - too few or too many assets per responsive search ad
  - exact duplicates within one ad (Google rejects these)
  - negative keywords that block your own keywords (the expensive, invisible one)

Usage:
    python3 validate_assets.py campaign.json
    python3 validate_assets.py --demo

Input JSON shape:
{
  "ad_groups": [
    {
      "name": "G1 | Delegated Authority",
      "headlines": ["...", "..."],
      "descriptions": ["...", "..."],
      "keywords": [["delegated authority audit", "Phrase"],
                   ["mga compliance monitoring", "Exact"]],
      "negatives": [["recruitment", "Broad"], ["nhs trust", "Phrase"]]
    }
  ],
  "shared_negatives": [["free template", "Phrase"], ["jobs", "Broad"]]
}

Match types: "Broad" | "Phrase" | "Exact"
Exit code 0 = clean, 1 = problems found.
"""

import json
import sys

HEADLINE_MAX = 30
DESCRIPTION_MAX = 90
HEADLINE_MIN_COUNT, HEADLINE_MAX_COUNT = 3, 15
DESCRIPTION_MIN_COUNT, DESCRIPTION_MAX_COUNT = 2, 4


def _norm(text):
    return " ".join(str(text).lower().split())


def blocks(negative, match_type, keyword):
    """True if this negative keyword would suppress this keyword.

    Broad negative  -> blocks if every token of the negative appears in the keyword.
    Phrase negative -> blocks if the negative appears as a contiguous substring.
    Exact negative  -> blocks only an identical keyword.
    """
    neg, kw = _norm(negative), _norm(keyword)
    mt = str(match_type).strip().lower()
    if mt.startswith("broad"):
        kw_tokens = set(kw.split())
        return all(tok in kw_tokens for tok in neg.split())
    if mt.startswith("phrase"):
        return neg in kw
    if mt.startswith("exact"):
        return neg == kw
    raise ValueError(f"Unknown match type: {match_type!r}")


def validate(data):
    errors, warnings = [], []
    groups = data.get("ad_groups", [])
    shared = [tuple(n) for n in data.get("shared_negatives", [])]

    if not groups:
        errors.append("No ad groups supplied.")

    all_keywords = []
    for g in groups:
        all_keywords += [(g.get("name", "?"), k) for k, _ in g.get("keywords", [])]

    for g in groups:
        name = g.get("name", "<unnamed>")
        heads = g.get("headlines", [])
        descs = g.get("descriptions", [])

        for h in heads:
            if len(h) > HEADLINE_MAX:
                errors.append(f"[{name}] headline {len(h)} chars (max {HEADLINE_MAX}): {h!r}")
        for d in descs:
            if len(d) > DESCRIPTION_MAX:
                errors.append(f"[{name}] description {len(d)} chars (max {DESCRIPTION_MAX}): {d!r}")

        if not HEADLINE_MIN_COUNT <= len(heads) <= HEADLINE_MAX_COUNT:
            errors.append(
                f"[{name}] {len(heads)} headlines "
                f"(need {HEADLINE_MIN_COUNT}-{HEADLINE_MAX_COUNT})"
            )
        if not DESCRIPTION_MIN_COUNT <= len(descs) <= DESCRIPTION_MAX_COUNT:
            errors.append(
                f"[{name}] {len(descs)} descriptions "
                f"(need {DESCRIPTION_MIN_COUNT}-{DESCRIPTION_MAX_COUNT})"
            )

        for label, items in (("headline", heads), ("description", descs)):
            seen = set()
            for item in items:
                key = _norm(item)
                if key in seen:
                    errors.append(f"[{name}] duplicate {label}: {item!r}")
                seen.add(key)

        if len(heads) < 8:
            warnings.append(f"[{name}] only {len(heads)} headlines; Google mixes better with 8+")
        if not g.get("keywords"):
            errors.append(f"[{name}] no keywords")

    # The expensive check: negatives that suppress your own keywords.
    for g in groups:
        gname = g.get("name", "?")
        scoped = [(n, mt, f"ad group {gname}") for n, mt in g.get("negatives", [])]
        for kw_owner, kw in [(o, k) for o, k in all_keywords if o == gname]:
            for neg, mt, origin in scoped:
                if blocks(neg, mt, kw):
                    errors.append(
                        f"CONFLICT: {origin} negative {neg!r} ({mt}) blocks keyword {kw!r}"
                    )

    for neg, mt in shared:
        for owner, kw in all_keywords:
            if blocks(neg, mt, kw):
                errors.append(
                    f"CONFLICT: shared negative {neg!r} ({mt}) blocks keyword "
                    f"{kw!r} in {owner}"
                )

    return errors, warnings


DEMO = {
    "ad_groups": [
        {
            "name": "Demo group",
            "headlines": [
                "Insurance Decision Governance",
                "Evidence For Your Authority Gap",   # 31 chars -> error
                "Built For Coverholders",
                "Built For Coverholders",            # duplicate -> error
            ],
            "descriptions": [
                "Fixed-scope assessment. One mandate, 90 days of decisions, three numbers.",
                "No software to install. Runs on your own decision data.",
            ],
            "keywords": [["coverholder audit", "Phrase"], ["binder compliance", "Phrase"]],
            "negatives": [["audit", "Broad"]],       # blocks own keyword -> error
        }
    ],
    "shared_negatives": [["free template", "Phrase"]],
}


def main():
    if "--demo" in sys.argv:
        data = DEMO
    elif len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        print(__doc__)
        return 1

    errors, warnings = validate(data)

    for w in warnings:
        print(f"WARN   {w}")
    for e in errors:
        print(f"ERROR  {e}")

    if errors:
        print(f"\n{len(errors)} error(s) — fix before upload.")
        return 1
    print(f"\nAll checks passed ({len(warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
