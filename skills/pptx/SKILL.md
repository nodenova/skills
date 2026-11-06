---
name: pptx
description: Read, edit, create or convert PowerPoint presentations (.pptx) in NodeNova Desk. Use for any task that opens, changes or produces slides - reading a deck, changing slide text or speaker notes, reordering, deleting or duplicating slides, a new deck from an outline or a firm template, or a deck to PDF or images. Not for Word documents, spreadsheets or PDFs.
---

# PowerPoint presentations (.pptx)

A .pptx is a zip of XML parts. `ppt/presentation.xml` lists the slides in show
order (`<p:sldIdLst>`); each slide is `ppt/slides/slideN.xml`, but N is not
the show order. Text is in `<a:t>` inside shapes (`<p:sp>`) and tables
(`<p:graphicFrame>`). Speaker notes are in `ppt/notesSlides/`.

**Skill folder.** This skill's scripts are in its `scripts/` folder, and its
longer guides are in `references/`. The folder's full path is printed at the
end of this text ("Skill directory"). Below, `S` is that path: start each
shell command with `S=<skill directory>;`. Read a guide with `cat "$S/references/<name>"`.

## Rules

1. **Never save a user's deck through pandoc or LibreOffice.** Both rebuild
   the whole file and lose animations, layouts and formatting. Use them only to
   read, to check, or to make a new file. To change a .pptx, edit only the XML
   that needs it.
2. **Work in `$TMPDIR`.** Unpacked parts, drafts and slide images go there,
   never in the user's folder. `read` opens files there by full path.
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

`soffice` runs one call at a time; wait for it to finish before the next.

## Edit text

```sh
S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W"
python3 "$S/scripts/ooxml.py" unpack "/abs/path/deck.pptx" "$W/x"
python3 "$S/scripts/pptx_outline.py" "/abs/path/deck.pptx" > "$W/before.txt"
grep -o '.\{0,300\}Revenue grew.\{0,300\}' "$W/x/ppt/slides/slide2.xml"
```

Take the slide's part from the outline. Slide XML is often one long line; do
not open it with `read`. A sentence is often split across runs (`<a:r>`, a
piece of text with one format), like `<a:t>Revenue grew </a:t>` then
`<a:t>12%</a:t>`: replace the runs that hold the phrase, putting the new text
in the first run (keep its `<a:rPr>`).

```sh
python3 "$S/scripts/ooxml.py" replace "$W/x/ppt/slides/slide2.xml" '<a:t>12%</a:t>' '<a:t>15%</a:t>'
```

It changes the part only if OLD occurs exactly once (`--all` for every
occurrence on purpose). When OLD or NEW has quotes of both kinds, write them
to files with a quoted heredoc and pass `"@$W/old.txt" "@$W/new.txt"`.

- Escape `&` as `&amp;`, `<` as `&lt;`, `>` as `&gt;` in new text. Never put a
  line break character in `<a:t>`.
- A new bullet: copy the neighbouring `<a:p>...</a:p>` and change its text.
- Keep new text about as long as the old. If it is much longer, shorten it or
  ask; do not shrink the font unasked.
- Speaker notes: the slide's notes part is in its `.rels`
  (`grep -o 'notesSlide[0-9]*.xml' "$W/x/ppt/slides/_rels/slide2.xml.rels"`);
  edit its `<a:t>` the same way.
- A picture: find its file in `ppt/slides/_rels/slideN.xml.rels`
  (`../media/image3.png`) and overwrite it in `$W/x/ppt/media/` with an image
  of the same type and shape, after checking no other slide uses it
  (`grep -l image3.png "$W"/x/ppt/slides/_rels/*`).

**Reorder, delete or duplicate slides:** `cat "$S/references/slides.md"`.

## Pack

```sh
python3 "$S/scripts/ooxml.py" pack "/abs/path/deck.pptx" "$W/x" "$W/out.pptx"
```

`pack` copies every untouched part from the original and checks the parts you
changed: well-formed XML, valid against the Office XML schema, relationships
and content types in order. It reports only problems your change added. On a
problem it writes nothing: fix it and pack again. "changed:" must list only
the parts you meant to touch.

## Create

Write the outline as Markdown and convert it; the Markdown format (slides,
notes, columns, tables, images) is in `cat "$S/references/new-deck.md"`:

```sh
pandoc "$W/deck.md" --slide-level=2 --reference-doc="/abs/path/firm-template.pptx" -o "$W/out.pptx"
```

Use the firm's template as `--reference-doc` whenever there is one (leave the
option out otherwise). This is fine because the file is new; never "redo" an
existing deck this way.

## Convert

```sh
soffice --headless --convert-to pdf --outdir "$W" "/abs/path/deck.pptx"    # deck -> PDF
pdftoppm -png -r 100 "$W/deck.pdf" "$W/slide"                               # PDF -> one PNG per slide
soffice --headless --convert-to pptx --outdir "$W" "/abs/path/deck.ppt"    # old .ppt -> new .pptx copy
```

## Check

1. `pack` passed (for a new file: `python3 "$S/scripts/ooxml.py" validate "$W/out.pptx"`).
2. Only the intended text changed:
   `python3 "$S/scripts/pptx_outline.py" "$W/out.pptx" > "$W/after.txt"; diff "$W/before.txt" "$W/after.txt"`
3. The changed slides look right: render them (as in "Read") and look at each
   one. Text stays inside its box and does not cover other shapes. If
   `soffice` makes no PDF, or the page count is wrong, go back.

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
