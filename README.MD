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
    references/         # deeper docs, templates and scripts the skill loads only when needed
```

Keeping detail in `references/` and out of `SKILL.md` is deliberate: the body stays short so it's cheap to keep in context, and the agent reads a reference file only when the task calls for it.

## Contributing

- One skill per directory under `skills/`, named in `kebab-case`.
- The `description` is the most important line you'll write: it's the only thing the agent sees when deciding whether to use the skill. State plainly what the skill does and the concrete triggers that should invoke it.
- Write the body for an agent, not a person. Lead with the gotchas that waste turns; prefer exact commands over prose.
- Push anything long or rarely needed into `references/` and link to it.

## License

[MIT](LICENSE)
