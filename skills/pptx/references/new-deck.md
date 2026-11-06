# New deck from Markdown (pandoc)

~~~markdown
---
title: Q3 Review
subtitle: Board meeting
---

# Results

## Revenue

- Revenue up 12%
- Costs flat

::: notes
Mention the North region.
:::

## Two options

:::::: columns
::: column
**Option A**: build in house
:::
::: column
**Option B**: buy
:::
::::::

## Figures

| Region | Q2 | Q3 |
|---|---:|---:|
| North | 100 | 112 |

## Chart

![](chart.png)
~~~

```sh
pandoc "$W/deck.md" --slide-level=2 -o "$W/out.pptx"
pandoc "$W/deck.md" --slide-level=2 --reference-doc="/abs/path/firm-template.pptx" -o "$W/out.pptx"
```

- The title block becomes the title slide. With `--slide-level=2`, each `##`
  starts a slide and a `#` becomes a section title slide.
- `::: notes` holds speaker notes. `:::: columns` with two `::: column` gives
  two columns.
- `--reference-doc` takes the template's masters, layouts, fonts and colours
  (not its slides). Without it the slides are plain white.
- Keep each slide short: a title and up to six bullets of a few words.
- Image paths are relative to where pandoc runs; run it from the folder with
  the images, or use full paths.

After building, render the deck and look at every slide (SKILL.md "Check").
