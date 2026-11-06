---
name: pptx
description: Read, edit, create or convert PowerPoint presentations (.pptx) in NodeNova Desk. Use for any task that opens, changes or produces slides - reading a deck, changing slide text, dates or footers, speaker notes, swapping a picture or logo, reordering, deleting or duplicating slides, a new deck from an outline or a firm template, or a deck to PDF or images. Not for Word documents, spreadsheets or PDFs.
---

# PowerPoint presentations (.pptx)

A .pptx is a zip of XML parts. `ppt/presentation.xml` lists the slides in show
order (`<p:sldIdLst>`); each slide is `ppt/slides/slideN.xml`, but N is not
the show order. Text is in `<a:t>` inside shapes (`<p:sp>`) and tables
(`<p:graphicFrame>`). Speaker notes are in `ppt/notesSlides/`.

**Every shell call starts fresh.** Variables, `cd` and functions from an
earlier call are gone. Start each command with
`S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W";` (`S` is the "Skill
directory" printed at the end of this text) and use full paths. Never run
`python3 -c "..."` with slide text inside the quotes; write a script file
with a quoted heredoc and run that. Guides are in `$S/references/`.

## Rules

1. **Never save a user's deck through pandoc, LibreOffice or python-pptx.**
   They rebuild the whole file and lose animations, layouts and formatting;
   use them only to read, check, or make a new file. Edit a .pptx with the
   scripts below.
2. **Work in `$TMPDIR`**, never in the user's folder.
3. **Look at every slide you change.** Text that is valid XML can still
   overflow its box on the slide.
4. **Change only what was asked**, and save only a file that passed the checks,
   with the `save` tool.

**Password-protected files** are not zips: `ooxml.py unpack` fails with
"File is not a zip file" and `file <path>` says "CDFV2 Encrypted". They
cannot be read or changed here; ask the user for an unprotected copy.

## Read

```sh
S=<skill directory>; python3 "$S/scripts/pptx_outline.py" "/abs/path/deck.pptx"
```

For each slide in show order: its part, id, relationship id and layout, each
shape's name and text (paragraphs joined by ` / `), and its speaker notes. To
see the slides, render them and open the images with `read`:

```sh
soffice --headless --convert-to pdf --outdir "$TMPDIR" "/abs/path/deck.pptx"
pdftoppm -png -r 50 -f 3 -l 3 "$TMPDIR/deck.pdf" "$TMPDIR/slide"   # slide 3; ls "$TMPDIR" for the name
```

`soffice` runs one call at a time; wait for it to finish before the next. If
`soffice` is not found, skip the render and verify with `pptx_outline.py`.

`pptx_outline.py` marks date, footer and slide-number placeholders and shows
fields as `{datetime1: 11/3/2026}`; `--layouts` also lists those on layouts
and masters. Pictures and logos are not text: `pptx_images.py list FILE`.

## Edit text

```sh
S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W"
python3 "$S/scripts/pptx_outline.py" "/abs/path/deck.pptx" > "$W/before.txt"
python3 "$S/scripts/pptx_replace_text.py" "/abs/path/deck.pptx" "$W/out.pptx" "Revenue grew 12%" "Revenue grew 15%" --slide 2
```

`pptx_replace_text.py IN OUT OLD NEW [--slide N] [--all] [--part PART]` finds
text by its words, even when PowerPoint split it across runs (`<a:r>`), and
changes only the XML needed; NEW takes the formatting of the run where OLD
starts. OLD and NEW are plain text, no XML. N is the slide number from the
outline; without `--slide` every slide is searched. OLD must occur once
unless `--all`. Speaker notes: `--part ppt/notesSlides/notesSlide1.xml` (the
notes part is in the slide's `.rels`). If OLD is not found, the error shows
the closest text: copy from it, not from memory. Errors are one line,
`ERROR: ...`; fix the command, do not fall back to `python3 -c`.

- Dates in footers sit in date placeholders, often on layouts and the master
  too: add `--all-parts` to search them as well. A `datetime` field refreshes
  itself when PowerPoint opens the file; add `--fixed` to make it plain text.
- `pptx_images.py list FILE` / `pptx_images.py replace IN OUT --image ppt/media/image1.png --with NEW.png [--fit]`
  swap a picture or logo (details: `cat "$S/references/pictures-and-dates.md"`).
  Never print an image file to the terminal; use `file` or the list command.
- Keep new text about as long as the old. If it is much longer, shorten it or
  ask; do not shrink the font unasked.
- **Reorder, delete or duplicate slides:** `cat "$S/references/slides.md"`.
  **Bullets, pictures and other XML-level edits:** `cat "$S/references/xml-edit.md"`.

## Create

Write the outline as Markdown and convert it; the Markdown format (slides,
notes, columns, tables, images) is in `cat "$S/references/new-deck.md"`:

```sh
S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W"
pandoc "$W/deck.md" --slide-level=2 --reference-doc="/abs/path/firm-template.pptx" -o "$W/out.pptx"
```

Use the firm's template as `--reference-doc` whenever there is one (leave the
option out otherwise). This is fine because the file is new; never "redo" an
existing deck this way.

## Convert

```sh
W="$TMPDIR/job1"; mkdir -p "$W"
soffice --headless --convert-to pdf --outdir "$W" "/abs/path/deck.pptx"    # deck -> PDF
pdftoppm -png -r 100 "$W/deck.pdf" "$W/slide"                               # PDF -> one PNG per slide
soffice --headless --convert-to pptx --outdir "$W" "/abs/path/deck.ppt"    # old .ppt -> new .pptx copy
```

## Check

1. The script said "checks passed" and "changed:" lists only the parts you
   meant (for a new file: `python3 "$S/scripts/ooxml.py" validate "$W/out.pptx"`).
2. Only the intended text changed (`before.txt` is made in "Edit text"):
   `python3 "$S/scripts/pptx_outline.py" "$W/out.pptx" > "$W/after.txt"; diff "$W/before.txt" "$W/after.txt"`
3. The changed slides look right: render them (as in "Read") and look at each
   one. Text stays inside its box and does not cover other shapes. If
   `soffice` makes no PDF, or the page count is wrong, go back. If `soffice`
   is not found, skip this step: step 2 is the check, and say the slides were
   not looked at.

## Save

Put the checked file in the user's folder with the `save` tool:
`from` is the file's full path (`echo "$W/out.pptx"` prints it), `path` is
where it goes, for example `/abs/path/deck.pptx` when the user asked to
change that file, or `/abs/path/deck (edited).pptx` for a new one next to it.
Replace the original only when the user asked to change that file.

`save` checks an Office file again in Desk itself and refuses a damaged one;
its answer lists the parts that changed, which must be only the ones you meant
to touch. In ask mode the user is asked to approve it first; if they decline,
the file was not saved: tell them, do not retry.

Older Desk without a `save` tool: `cp "$W/out.pptx" "/abs/path/..."` in the
shell. If that fails with "Read-only file system" or "Permission denied", tell
the user the file is ready at its full `$TMPDIR` path and could not be saved.

Then tell the user in one or two lines what changed and where it was saved.
