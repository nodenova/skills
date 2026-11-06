---
name: docx
description: Read, edit, create or convert Word documents (.docx, .dotx) in NodeNova Desk. Use for any task that opens, changes or produces a Word file - find and replace, rewording a clause, tracked changes, comments, accepting changes, tables, headers and footers, a new report, memo or letter from text, or a docx to PDF. Not for PDFs, spreadsheets or slides.
---

# Word documents (.docx)

A .docx is a zip of XML parts. The text is in `word/document.xml`; headers and
footers in `word/header1.xml`, `word/footer1.xml`; comments in
`word/comments.xml`; styles in `word/styles.xml`.

**Skill folder.** This skill's scripts are in its `scripts/` folder, and its
longer guides are in `references/`. The folder's full path is printed at the
end of this text ("Skill directory"). Below, `S` is that path: start each
shell command with `S=<skill directory>;`. Read a guide with `cat "$S/references/<name>"`.

## Rules

1. **Never save a user's file through pandoc or LibreOffice.** Both rebuild the
   whole file and lose formatting. Use them only to read, to check, or to make
   a new file. To change a .docx, edit only the XML that needs it.
2. **Work in `$TMPDIR`.** Unpacked parts, drafts and page images go there,
   never in the user's folder. `read` opens files there by full path.
3. **Change only what was asked.** Do not restyle or "clean up" other parts.
4. **Save only a file that passed the checks**, with the `save` tool (see "Save").

**Password-protected files** are not zips: `ooxml.py unpack` fails with
"File is not a zip file" and `file <path>` says "CDFV2 Encrypted". They
cannot be read or changed here; ask the user for an unprotected copy.

## Read

```sh
pandoc -t markdown "/abs/path/file.docx"                       # text, headings, lists, tables
pandoc --track-changes=all -t markdown "/abs/path/file.docx"   # also insertions, deletions, comments
```

To see the layout, render a page and open the image with `read`:

```sh
soffice --headless --convert-to pdf --outdir "$TMPDIR" "/abs/path/file.docx"
pdftoppm -png -r 80 -f 1 -l 1 "$TMPDIR/file.pdf" "$TMPDIR/page"   # then read $TMPDIR/page-1.png
```

`soffice` runs one call at a time; wait for it to finish before the next.

## Edit

```sh
S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W"
python3 "$S/scripts/ooxml.py" unpack "/abs/path/file.docx" "$W/x"
pandoc -t plain --track-changes=all "/abs/path/file.docx" > "$W/before.txt"
python3 "$S/scripts/docx_find.py" "/abs/path/file.docx" "late payment"
```

`docx_find.py` prints each paragraph that contains the words: its text, its
runs, and its exact XML. (`document.xml` is usually one very long line, so do
not open it with `read`.) A run (`<w:r>`) is a piece of text with one format.
Text is often split across runs, like `'Revenue grew' | ' ' | '12%'`; then
replace the runs that hold the phrase. For a header or footer, add the part:
`... "Draft" word/header1.xml`.

Replace with OLD copied exactly from that output. It changes the part only if
OLD occurs exactly once (`--all` changes every occurrence on purpose):

```sh
python3 "$S/scripts/ooxml.py" replace "$W/x/word/document.xml" '<w:t>within 30 days</w:t>' '<w:t>within 14 days</w:t>'
```

When the XML has quotes of both kinds, write OLD and NEW to files with a
quoted heredoc (`cat > "$W/old.txt" <<'EOF'` ... `EOF`) and pass
`"@$W/old.txt" "@$W/new.txt"`.

Then pack:

```sh
python3 "$S/scripts/ooxml.py" pack "/abs/path/file.docx" "$W/x" "$W/out.docx"
```

`pack` copies every untouched part from the original and checks the parts you
changed: well-formed XML, valid against the Office XML schema, relationships
and content types in order. It compares with the original and reports only
problems your change added. On a problem it writes nothing and says what is
wrong: fix it and pack again. "changed:" lists the parts you touched; it must
hold only the ones you meant to.

Before writing XML, read `cat "$S/references/word-xml.md"`: text escaping,
spaces, line breaks, new paragraphs, table rows, pictures, element order.

**Tracked changes, comments, accepting changes:** `cat "$S/references/tracked-changes-and-comments.md"`.
Use tracked changes whenever the user wants to review what changed (a
redline). To accept all changes: `python3 "$S/scripts/docx_accept.py" "$W/x/word/document.xml"`,
then pack.

## Create

Write the content as Markdown in `$TMPDIR` and convert it:

```sh
pandoc "$W/report.md" -o "$W/out.docx"
pandoc "$W/report.md" --reference-doc="/abs/path/firm-template.docx" -o "$W/out.docx"   # firm's styles, fonts, page size
pandoc "$W/report.md" --toc -o "$W/out.docx"                                           # with a table of contents
```

`#`/`##` become Heading 1/2; `**bold**`, lists and pipe tables become real
Word formatting. Use the firm's template or an earlier document as
`--reference-doc` whenever there is one; without it, pages are US Letter in
pandoc's plain style. For a page break, put a raw block in the Markdown:

~~~markdown
```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```
~~~

This is fine because the file is new. Never "redo" an existing document this
way; edit its XML.

## Convert

```sh
soffice --headless --convert-to pdf --outdir "$W" "/abs/path/file.docx"   # docx -> PDF
soffice --headless --convert-to docx --outdir "$W" "/abs/path/file.doc"   # old .doc -> new .docx copy
```

## Check

1. `pack` passed (or, for a new file, `python3 "$S/scripts/ooxml.py" validate "$W/out.docx"`;
   pandoc's own output has a few known schema slips that Word accepts).
2. The text changed only where intended:
   `pandoc -t plain --track-changes=all "$W/out.docx" > "$W/after.txt"; diff "$W/before.txt" "$W/after.txt"`
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
