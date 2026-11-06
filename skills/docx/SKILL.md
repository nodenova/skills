---
name: docx
description: Read, edit, create or convert Word documents (.docx, .dotx) in NodeNova Desk. Use for any task that opens, changes or produces a Word file - find and replace, rewording a clause, tracked changes, comments, accepting changes, tables, headers and footers, a new report, memo or letter from text, or a docx to PDF. Not for PDFs, spreadsheets or slides.
---

# Word documents (.docx)

A .docx is a zip of XML parts: text in `word/document.xml`, headers and
footers in `word/header1.xml`, `word/footer1.xml`.

**Every shell call starts fresh.** Variables, `cd` and functions from an
earlier call are gone. Start each command with
`S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W";` (`S` is the "Skill
directory" printed at the end of this text) and use full paths. Never run
`python3 -c "..."` with document text inside the quotes: curly quotes and
apostrophes break it. Write a script file with a quoted heredoc
(`cat > "$W/t.py" <<'EOF'`) and run that. Guides are in `$S/references/`.

## Rules

1. **Never save a user's file through pandoc, LibreOffice or python-docx.**
   They rebuild the whole file and lose formatting; use them only to read,
   check, or make a new file. Edit a .docx with the scripts below.
2. **Work in `$TMPDIR`**, never in the user's folder.
3. **Change only what was asked.**
4. **Save only a file that passed the checks**, with the `save` tool.

**Password-protected files** (`file <path>` says "CDFV2 Encrypted") cannot be
read or changed here; ask for an unprotected copy.

## Read

```sh
pandoc -t markdown "/abs/path/file.docx"                       # text, headings, lists, tables
pandoc --track-changes=all -t markdown "/abs/path/file.docx"   # also insertions, deletions, comments
```

To see the layout, render a page and `read` the image (one `soffice` at a time):

```sh
W="$TMPDIR/job1"; mkdir -p "$W"; soffice --headless --convert-to pdf --outdir "$W" "/abs/path/file.docx"
pdftoppm -png -r 80 -f 1 -l 1 "$W/file.pdf" "$W/page"   # then read $W/page-1.png
```

## Edit

To change formatting or wording, use these. They find text by its words (even
when Word split it across runs), edit only the XML needed and write OUT
through the checked pack. You never write XML:

```sh
S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W"
python3 "$S/scripts/docx_find.py" "/abs/path/file.docx" "Invitation to Tender"
python3 "$S/scripts/docx_format.py" "/abs/path/file.docx" "$W/out.docx" --paragraph-containing "Invitation to Tender" --color FF0000
python3 "$S/scripts/docx_replace_text.py" "/abs/path/file.docx" "$W/out.docx" "within 30 days" "within 14 days"
```

- `docx_find.py FILE TEXT` lists the paragraphs with TEXT: number, text, each
  run with its formatting. FILE may also be an unpacked folder or one part.
- `docx_format.py IN OUT PICK FORMAT...`. PICK: `--paragraph N` (number from
  `docx_find.py`) or `--paragraph-containing TEXT` with `--occurrence K` or
  `--all` when several paragraphs match. FORMAT: `--color FF0000|red`,
  `--bold|--no-bold`, `--italic|--no-italic`, `--underline|--no-underline`,
  `--size 14`, `--highlight yellow`, `--font Arial`. All runs of the paragraph
  change, and the old colour (theme colour too) is replaced.
- `docx_replace_text.py IN OUT OLD NEW [--all]`: plain text, no XML. NEW takes
  the formatting of the run where OLD starts.
- Header or footer: `--part word/header1.xml` (`docx_find.py FILE TEXT word/header1.xml`).
- A second edit starts from the first result: IN `"$W/out.docx"`, OUT `"$W/out2.docx"`.
- Errors are one line, `ERROR: ...`. If TEXT or OLD is not found, it shows the
  closest text: copy from it, not from memory. Fix the command; do not fall
  back to `python3 -c`.

Only for what these cannot do (new paragraphs, table rows, pictures, tracked
changes, comments) edit the XML by hand: `cat "$S/references/word-xml.md"`,
and for redlines and comments also `cat "$S/references/tracked-changes-and-comments.md"`.

## Create

Write the content as Markdown in `$W` and convert it:

```sh
pandoc "$W/report.md" -o "$W/out.docx"
pandoc "$W/report.md" --reference-doc="/abs/path/firm-template.docx" -o "$W/out.docx"   # firm's styles, fonts, page size
pandoc "$W/report.md" --toc -o "$W/out.docx"                                           # with a table of contents
```

`#`/`##` become Heading 1/2; `**bold**`, lists and pipe tables become real
Word formatting. Use the firm's template as `--reference-doc` whenever there
is one. For a page break, put a raw block in the Markdown:

~~~markdown
```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```
~~~

Never "redo" an existing document this way; edit it with the scripts above.

## Convert

```sh
soffice --headless --convert-to pdf --outdir "$W" "/abs/path/file.docx"   # docx -> PDF
soffice --headless --convert-to docx --outdir "$W" "/abs/path/file.doc"   # old .doc -> new .docx copy
```

## Check

1. The script says "checks passed" and "changed:" lists only the part you
   meant (for a new file: `python3 "$S/scripts/ooxml.py" validate "$W/out.docx"`;
   pandoc output has a few schema slips Word accepts).
2. The text changed only where intended:
   `pandoc -t plain --track-changes=all "/abs/path/file.docx" > "$W/before.txt"; pandoc -t plain --track-changes=all "$W/out.docx" > "$W/after.txt"; diff "$W/before.txt" "$W/after.txt"`
3. It opens and looks right: render the changed page as in "Read" and look at
   it. If `soffice` makes no PDF, the file is broken; do not save it.

## Save

Put the checked file in the user's folder with the `save` tool:
`from` is the file's full path (`echo "$W/out.docx"` prints it), `path` is
where it goes, for example `/abs/path/file.docx` when the user asked to
change that file, or `/abs/path/file (edited).docx` for a new one next to it.
Replace the original only when the user asked to change that file.

`save` checks an Office file again in Desk itself and refuses a damaged one;
its answer lists the parts that changed, which must be only the ones you meant
to touch. In ask mode the user is asked to approve it first; if they decline,
the file was not saved: tell them, do not retry.

Older Desk without a `save` tool: `cp "$W/out.docx" "/abs/path/..."` in the
shell. If that fails with "Read-only file system" or "Permission denied", tell
the user the file is ready at its full `$TMPDIR` path and could not be saved.

Then tell the user in one or two lines what changed and where it was saved.
