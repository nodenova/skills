# Google Ads Editor import format

Generate these alongside any UI build. They make rebuilds trivial, survive session loss, and turn an hour of clicking into one paste. Import via **Google Ads Editor → Account → Import → From file** (or paste text).

Write CSVs as `utf-8-sig` — Editor expects the BOM.

## File 1 — campaign, ad groups, keywords, ads

One CSV, one row per entity. Leave irrelevant columns blank; Editor reads each row by the columns it has filled.

**Columns**

```
Campaign, Campaign Type, Campaign Status, Campaign Daily Budget, Bid Strategy Type,
Start Date, End Date, Networks, Languages, Ad Group, Max CPC, Ad Group Status,
Keyword, Criterion Type, Ad type,
Headline 1..15, Description 1..4, Final URL, Path 1, Path 2, Status
```

**Row types**

| Row | Fill these |
|---|---|
| Campaign | Campaign, Campaign Type `Search`, Campaign Status `Paused`, budget, Bid Strategy Type `Maximize clicks`, dates, Networks `Google search`, Languages `en` |
| Ad group | Campaign, Ad Group, Max CPC, Ad Group Status |
| Keyword | Campaign, Ad Group, Keyword, Criterion Type, Status |
| Ad | Campaign, Ad Group, Ad type `Responsive search ad`, Headline 1..n, Description 1..n, Final URL, Path 1, Path 2, Status |

**Always set `Campaign Status` to `Paused`.** An import that lands enabled starts spending immediately.

Write keywords bare — the match type lives in `Criterion Type`, not in brackets or quotes:

| Criterion Type | Meaning |
|---|---|
| `Broad` | broad match |
| `Phrase` | phrase match |
| `Exact` | exact match |

## File 2 — ad group negative keywords

```
Campaign, Ad Group, Keyword, Criterion Type
```

`Criterion Type` becomes `Negative Broad`, `Negative Phrase`, or `Negative Exact`.

## File 3 — shared negative list

Editor doesn't reliably create shared lists on import. Produce this as a plain list for pasting into **Tools → Shared library → Negative keyword lists**, then attach it to the campaign:

```
Keyword, Match Type
```

Quote phrase negatives (`"free template"`), leave broad ones bare. Ship a `.txt` of the same terms, one per line, for direct pasting into the web UI.

## Gotchas

- Duplicate negatives across ad-group and shared level are harmless — Google dedupes at serve time. Don't spend effort reconciling them.
- Editor errors on duplicate keywords *within the same list*, not across levels.
- Match-type brackets inside the `Keyword` column are a common cause of "keyword not eligible" — keep them out.
- Campaign total (lifetime) budgets aren't expressible in the standard Editor campaign row; set those in the web UI after import.
