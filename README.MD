# Skills

A collection of [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) — packaged know-how that teaches an AI agent how to do a real task well, instead of re-discovering the method (and the dead ends) every time.

A skill is a folder with a `SKILL.md`. The frontmatter `description` tells the agent *when* to reach for the skill; the body tells it *how* to do the job — hardened against the specific ways an agent tends to flail on that task. Skills are model-portable: the same folder works anywhere that supports the format — Claude Code, the Claude apps, and agents built on the Claude API / Agent SDK.

## Skills

| Skill | What it does |
|-------|--------------|
| [`miro-board-explorer`](skills/miro-board-explorer) | Reads and extracts the real content of a Miro board from a share link — change requests, comments, frame names, and the red annotations drawn on mockups — and turns it into a dev-ready summary. Drives `agent-browser` live and encodes the moves that keep an agent from getting lost on Miro's WebGL canvas. |
| [`figma-implement-design`](skills/figma-implement-design) | Reads a Figma design through the browser and implements it as UI at 100% fidelity. Drives the Claude-in-Chrome extension against the user's signed-in Figma and extracts exact specs (font, size, line-height, letter-spacing, radius, padding, gap, autolayout, fills) from the inspect panel as DOM text instead of eyeballing pixels — then maps them onto the project's own tokens and verifies element-by-element. Encodes the moves that keep an agent from mis-selecting nodes or over-trusting a full-page glance. |

## Install

Drop a skill into the directory your agent scans for skills. For Claude Code that's:

- **Personal** (every project): `~/.claude/skills/`
- **Project** (checked in with your repo): `.claude/skills/`

Clone and copy the one you want:

```bash
git clone https://github.com/node-nova/skills.git
cp -r skills/skills/miro-board-explorer ~/.claude/skills/
```

Or symlink it to stay current with `git pull`:

```bash
ln -s "$(pwd)/skills/miro-board-explorer" ~/.claude/skills/miro-board-explorer
```

Other runtimes load skills differently (e.g. the Agent SDK takes a skills directory in config) — check your runtime's docs for where the folder goes.

## Use

You don't invoke skills by name. Describe the task, and the agent matches it against each skill's `description` and loads the relevant one:

> Pull the change requests off this Miro board: https://miro.com/app/board/…

> Implement this screen to match the design: https://www.figma.com/design/…?node-id=…

Some skills depend on external tools — `miro-board-explorer` needs the `agent-browser` CLI; `figma-implement-design` drives the [Claude-in-Chrome](https://www.anthropic.com/news/claude-in-chrome) browser extension against a Chrome that's signed into Figma. Each skill's `SKILL.md` lists its requirements up top.

## Repo layout

```
skills/
  <skill-name>/
    SKILL.md            # frontmatter (name, description, allowed-tools) + the method
    references/         # deeper docs the skill loads only when needed
```

Keeping detail in `references/` and out of `SKILL.md` is deliberate: the body stays short so it's cheap to keep in context, and the agent reads a reference file only when the task calls for it.

## Contributing

- One skill per directory under `skills/`, named in `kebab-case`.
- The `description` is the most important line you'll write: it's the only thing the agent sees when deciding whether to use the skill. State plainly what the skill does and the concrete triggers that should invoke it.
- Write the body for an agent, not a person. Lead with the gotchas that waste turns; prefer exact commands over prose.
- Push anything long or rarely needed into `references/` and link to it.

## License

[MIT](LICENSE)
