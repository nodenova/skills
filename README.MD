# Skills

A collection of [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) — packaged know-how that teaches an AI agent how to do a real task well, instead of re-discovering the method (and the dead ends) every time.

A skill is a folder with a `SKILL.md`. The frontmatter `description` tells the agent *when* to reach for the skill; the body tells it *how* to do the job — hardened against the specific ways an agent tends to flail on that task. Skills are model-portable: the same folder works anywhere that supports the format — Claude Code, the Claude apps, and agents built on the Claude API / Agent SDK.

## Skills

| Skill | What it does |
|-------|--------------|
| [`miro-board-explorer`](skills/miro-board-explorer) | Reads and extracts the real content of a Miro board from a share link — change requests, comments, frame names, and the red annotations drawn on mockups — and turns it into a dev-ready summary. Drives `agent-browser` live and encodes the moves that keep an agent from getting lost on Miro's WebGL canvas. |
| [`figma-implement-design`](skills/figma-implement-design) | Reads a Figma design through the browser and implements it as UI at 100% fidelity. Drives the Claude-in-Chrome extension against the user's signed-in Figma and extracts exact specs (font, size, line-height, letter-spacing, radius, padding, gap, autolayout, fills) from the inspect panel as DOM text instead of eyeballing pixels — then maps them onto the project's own tokens and verifies element-by-element. Encodes the moves that keep an agent from mis-selecting nodes or over-trusting a full-page glance. |
| [`google-search-campaign`](skills/google-search-campaign) | Builds, launches, audits and verifies a Google Ads Search campaign from a spreadsheet of headlines, descriptions, keywords and negatives. Checks demand exists before building, validates assets against Google's limits with a script (not by eye), wires conversion tracking end to end, and drives the Ads UI without tripping its defaults. Nothing goes live without explicit approval. |
| [`meta-leads-campaign-setup`](skills/meta-leads-campaign-setup) | Sets up a Meta (Facebook/Instagram) Leads campaign that sends traffic to a lead magnet on your own site: Pixel + Conversions API tracking with a shared `eventID`, the Events Manager traps (Test Events, URL rules, lag), account prerequisites, and the Ads Manager build via Claude-in-Chrome with Meta's AI enhancements switched off. Leaves the campaign as a draft; never publishes. |
| [`tender-portal-bidding`](skills/tender-portal-bidding) | Registers on public-sector e-procurement portals and works through selection questionnaires. Gets through the registration wall first, reads the bid pack before any bid/no-bid call, checks the deliverable's real shape against the notice, and never guesses on a warranted form. |
| [`docx`](skills/docx) | Reads, edits and creates Word documents in NodeNova Desk: edits only the XML that changes (`docx_format.py` for colour, bold, size and fonts and `docx_replace_text.py` for wording across split runs in one or a few places; one measured Python script over the XML for a change across the whole document; tracked changes, comments, accepting changes), checks every edit against the ECMA-376 schemas and the package wiring, creates new documents with pandoc and a firm template, and checks each result by text diff and a rendered page. |
| [`xlsx`](skills/xlsx) | Reads, edits and creates Excel workbooks in NodeNova Desk: `xlsx_set.py` cell edits that keep formats, a recalculation check that catches stale formula results and errors, and a stdlib workbook builder (sheets, bold header, number formats, formulas). |
| [`pptx`](skills/pptx) | Reads, edits and creates PowerPoint decks in NodeNova Desk: slide outline in show order, `pptx_replace_text.py` text and notes edits across split runs, reorder/delete/duplicate slides, new decks from Markdown with the firm template, and a look at every changed slide. |
| [`pdf`](skills/pdf) | Works with PDFs in NodeNova Desk: text and tables, OCR for scans, merge/split/rotate, passwords, form filling, stamps and letterheads, and making PDFs from documents, `pdf_find.py` to locate a phrase by page. |

## Install

Drop a skill into the directory your agent scans for skills. For Claude Code that's:

- **Personal** (every project): `~/.claude/skills/`
- **Project** (checked in with your repo): `.claude/skills/`

Clone and copy the one you want:

```bash
git clone https://github.com/nodenova/skills.git
cp -r skills/skills/miro-board-explorer ~/.claude/skills/
```

Or symlink it to stay current with `git pull`:

```bash
ln -s "$(pwd)/skills/skills/miro-board-explorer" ~/.claude/skills/miro-board-explorer
```

Other runtimes load skills differently (e.g. the Agent SDK takes a skills directory in config) — check your runtime's docs for where the folder goes.

## Use

You don't invoke skills by name. Describe the task, and the agent matches it against each skill's `description` and loads the relevant one:

> Pull the change requests off this Miro board: https://miro.com/app/board/…

> Implement this screen to match the design: https://www.figma.com/design/…?node-id=…

> Set up Google Ads from this sheet of headlines and keywords, but don't launch it.

> Build the Meta leads campaign for the assessment page from the launch pack.

> Register on this tender portal and tell me whether we can actually bid.

Some skills depend on external tools — `miro-board-explorer` needs the `agent-browser` CLI; `figma-implement-design`, `google-search-campaign` and `meta-leads-campaign-setup` drive the [Claude-in-Chrome](https://www.anthropic.com/news/claude-in-chrome) browser extension against a Chrome that's signed into Figma, Google Ads or Meta Business respectively. The ad skills never enter passwords or publish on their own: you sign in, and you approve anything that spends money. See each skill's `SKILL.md` for details.

## Repo layout

```
skills/
  <skill-name>/
    SKILL.md            # frontmatter (name, description, allowed-tools) + the method
    scripts/            # code the skill runs (the agent runs it, never retypes it)
    references/         # deeper docs the skill loads only when needed
shared/
  ooxml.py              # one source for the Office XML helper; copied into docx, xlsx, pptx
tools/
  sync-shared.sh        # copy shared/ into the skills; --check fails if a copy drifted
tests/
  desk/                 # acceptance test inside NodeNova Desk's agent image (run.sh)
```

Each skill folder works on its own (skills are pinned and installed one by one), so `ooxml.py` is copied into each office skill rather than linked. Edit `shared/ooxml.py`, then run `tools/sync-shared.sh`.

### Office skills and NodeNova Desk

`docx`, `xlsx`, `pptx` and `pdf` are written for NodeNova Desk's agent and its dev image (`ghcr.io/nodenova/desk-agent`, `nodenova/runtime/Dockerfile` in the desk repo), which bakes them in at `/opt/nodenova/skills`. They rely on:

- `skill_read` ending with `[Skill directory: <path>]`, so the agent finds `scripts/` and `references/` (desk D49);
- LibreOffice, pandoc, poppler, qpdf, pdftk, tesseract, Python 3 with `lxml` and `defusedxml`;
- the ECMA-376 transitional and packaging schemas plus W3C `xml.xsd` at `$NN_OOXML_SCHEMAS` (default `/opt/nodenova/ooxml-schemas`). The image downloads them from Ecma at build time; they are not copied into this repo. Without lxml or the schemas, `ooxml.py` still checks well-formedness and package wiring and says the schema check was skipped.

Finished files reach the user's folder through Desk's `save` tool, which runs its own Office package check (desk D51); the skills fall back to `cp` on older builds without it.

The image builds the skills from the commit pinned in the desk repo's `nodenova/runtime/skills.json`, and the desktop app from the commit the shipped agent version pins (`skills` in its `agent.json`); update those hashes to ship a change.

### Test on Desk

`tests/desk/run.sh [image]` runs the acceptance test inside Desk's agent image (default `nn-desk-agent:dev`, built from the desk repo with this checkout as its `skills` build context). It drives the image's own tool server the way the agent does, `skill_list`, `skill_read`, `read`, `shell` (sandboxed, offline) and `save`, and works through every skill on files written by pandoc and LibreOffice: edits across split runs, tracked changes and comments, accepting changes, cell edits with recalculation, new workbooks, slide edits and duplication, merging, forms, OCR, and broken files that the skills' `pack` and Desk's `save` must both refuse. It checks results (text, values, pages, parts changed), not only exit codes. The image is Debian 13 with Node.js 26 LTS, Python 3.14 (lxml 6.1), LibreOffice 25.2, pandoc 3.1 and tesseract 5.5.

Keeping detail in `references/` and out of `SKILL.md` is deliberate: the body stays short so it's cheap to keep in context, and the agent reads a reference file only when the task calls for it.

## Contributing

- One skill per directory under `skills/`, named in `kebab-case`.
- The `description` is the most important line you'll write: it's the only thing the agent sees when deciding whether to use the skill. State plainly what the skill does and the concrete triggers that should invoke it.
- Write the body for an agent, not a person. Lead with the gotchas that waste turns; prefer exact commands over prose.
- Push anything long or rarely needed into `references/` and link to it.

## License

[MIT](LICENSE)
