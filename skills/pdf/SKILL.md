---
name: pdf
description: Read, combine, split, fill, stamp, OCR or create PDF files in NodeNova Desk. Use for any task with a PDF - reading text or tables, finding something in a long PDF, scanned pages, merging, splitting, extracting, rotating or reordering pages, filling a PDF form, adding a watermark or stamp, passwords, making a PDF from a document or from Markdown, or PDF pages to images. Not for editing Word, Excel or PowerPoint files themselves.
---

# PDF files

What you have: the shell (offline, nothing can be installed), poppler
(`pdfinfo`, `pdftotext`, `pdftoppm`, `pdfimages`, `pdfseparate`, `pdfunite`),
`qpdf`, `pdftk`, `tesseract` (OCR, English only), `soffice` (LibreOffice:
Writer, Calc, Impress), `pandoc`, ImageMagick `convert` (cannot read or
write PDFs here), Python 3 (with lxml in Desk's image; no PDF libraries).
There is no pypdf, no reportlab and no Ghostscript.

**Every shell call starts fresh:** variables, `cd` and functions are gone, so
use full paths and set `S=<skill directory>` (printed at the end of this text)
in the same command. Never use `python3 -c` with text from a file in the
quotes; write a script file with a quoted heredoc.

## Rules

1. **Work in `$TMPDIR`.** Page images, split pages and drafts go there, never
   in the user's folder. `read` can open files there by full path
   (`echo $TMPDIR`); `read` cannot open a PDF itself.
2. **Never overwrite the user's PDF.** Every operation writes a new file in
   `$TMPDIR`; save it under a clear new name (`contract (signed pages).pdf`).
3. **The text of a PDF cannot be edited here.** To change wording, change the
   source document (docx, xlsx, pptx) and export it again; if there is no
   source, tell the user.
4. **Look at the result** before you save it (see "Check").

## Read

```sh
pdfinfo "/abs/path/file.pdf"                          # pages, page size, encrypted?, producer
pdftotext -layout "/abs/path/file.pdf" - | head -200  # text, columns and tables kept in place
pdftotext -layout -f 3 -l 5 "/abs/path/file.pdf" -    # pages 3 to 5 only
```

For a long PDF, write the text to a file and search it:

```sh
pdftotext -layout "/abs/path/file.pdf" "$TMPDIR/file.txt"
grep -n -i "termination" "$TMPDIR/file.txt"
```

To find the pages of a match (any case; `--pages 3-9` limits the range):

```sh
S=<skill directory>; python3 "$S/scripts/pdf_find.py" "/abs/path/file.pdf" "termination"
```

To see a page (layout, signatures, stamps, charts), render it and open the
image with `read`:

```sh
pdftoppm -png -r 80 -f 2 -l 2 "/abs/path/file.pdf" "$TMPDIR/p"   # writes $TMPDIR/p-2.png (or p-02.png ...; ls to see)
```

Use `-r 80` to look at a page, `-r 150` to read small print, `-r 300` for OCR.

Tables: `pdftotext -layout` keeps columns lined up; read the columns from
that text. Check a few numbers against the page image.

Embedded images: `pdfimages -list file.pdf` lists them; `pdfimages -png file.pdf "$TMPDIR/img"` extracts them.

## Scanned PDFs (no text)

If `pdftotext` prints nothing or garbage, the pages are pictures. Read them
with OCR:

```sh
mkdir -p "$TMPDIR/ocr" && pdftoppm -png -r 300 "/abs/path/scan.pdf" "$TMPDIR/ocr/p"
for f in "$TMPDIR"/ocr/p-*.png; do echo "=== $f"; tesseract "$f" - 2>/dev/null; done > "$TMPDIR/scan.txt"
```

OCR is English only and makes mistakes with numbers, names and stamps:
check important values against the page image.

To give the user a searchable copy of the scan (text they can select and
search):

```sh
for f in "$TMPDIR"/ocr/p-*.png; do tesseract "$f" "${f%.png}" pdf 2>/dev/null; done
pdfunite "$TMPDIR"/ocr/p-*.pdf "$TMPDIR/scan (searchable).pdf"
```

Long scans take a while (several seconds per page): pass a larger `timeout`
to the shell call.

## Pages: merge, split, extract, rotate, reorder

```sh
qpdf --empty --pages a.pdf b.pdf c.pdf -- "$TMPDIR/merged.pdf"           # merge in this order
qpdf "/abs/path/file.pdf" --pages . 3-5 -- "$TMPDIR/pages 3-5.pdf"       # extract pages
qpdf "/abs/path/file.pdf" --pages . 1-2,6-z -- "$TMPDIR/without 3-5.pdf" # drop pages (z = last)
qpdf "/abs/path/file.pdf" --pages . 3,1,2,4-z -- "$TMPDIR/reordered.pdf" # new order
qpdf --empty --pages a.pdf 1 b.pdf 2-3 -- "$TMPDIR/mix.pdf"             # pages from several files
qpdf "/abs/path/file.pdf" --rotate=+90:2,4 "$TMPDIR/rotated.pdf"         # rotate pages 2 and 4 clockwise
pdfseparate "/abs/path/file.pdf" "$TMPDIR/page-%d.pdf"                   # one file per page
```

Run qpdf on files whose paths have spaces with quotes. A warning from qpdf
with exit 3 still wrote the file; check it.

## Passwords

```sh
qpdf --password='secret' --decrypt "/abs/path/locked.pdf" "$TMPDIR/unlocked.pdf"
qpdf --encrypt 'open-pw' 'owner-pw' 256 -- "/abs/path/file.pdf" "$TMPDIR/protected.pdf"
```

Only remove a password the user gave you, from a file they are entitled to open.

## Fill a PDF form

First see whether it has form fields:

```sh
pdftk "/abs/path/form.pdf" dump_data_fields_utf8
```

Each field has a `FieldName`, a `FieldType` (Text, Button, Choice) and, for
checkboxes and choices, `FieldStateOption` lines with the allowed values. Write
an XFDF file with the values (UTF-8, so accents work), then fill:

```sh
cat > "$TMPDIR/values.xfdf" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<xfdf xmlns="http://ns.adobe.com/xfdf/"><fields>
  <field name="FullName"><value>Jane Doe</value></field>
  <field name="AgreeTerms"><value>Yes</value></field>
</fields></xfdf>
EOF
pdftk "/abs/path/form.pdf" fill_form "$TMPDIR/values.xfdf" output "$TMPDIR/filled.pdf"
pdftk "$TMPDIR/filled.pdf" dump_data_fields_utf8 | grep -E "FieldName|FieldValue"
```

- Use the exact `FieldName` and, for a checkbox, one of its
  `FieldStateOption` values (often `Yes` or `On`, not `true`).
- Escape `&` as `&amp;` and `<` as `&lt;` in values.
- To lock the values into the page, add `flatten` after `output ...`. Some
  forms then lose the values: check with `pdftotext` and a page image; if
  they are gone, give the user the unflattened file.
- If `dump_data_fields_utf8` prints nothing, the form has no fields (it is a
  flat or scanned page). It cannot be filled reliably here: tell the user,
  and offer to write the answers in a separate document.

## Watermark, stamp, letterhead

Make a one-page PDF with the mark (a docx or Markdown converted as in
"Create", same page size as the target), then:

```sh
pdftk "/abs/path/file.pdf" stamp "$TMPDIR/mark.pdf" output "$TMPDIR/stamped.pdf"       # on top of every page
pdftk "/abs/path/file.pdf" background "$TMPDIR/mark.pdf" output "$TMPDIR/on-letterhead.pdf"  # behind every page
pdftk "/abs/path/file.pdf" multistamp "$TMPDIR/marks.pdf" output "$TMPDIR/out.pdf"     # page n of marks on page n
```

`pdfinfo` shows each file's page size; use the same for the mark.

## Title, author and other properties

```sh
pdftk "/abs/path/file.pdf" dump_data_utf8 | grep -A1 InfoKey
cat > "$TMPDIR/info.txt" <<'EOF'
InfoBegin
InfoKey: Title
InfoValue: Annual Report 2025
EOF
pdftk "/abs/path/file.pdf" update_info_utf8 "$TMPDIR/info.txt" output "$TMPDIR/with-title.pdf"
```

## Create a PDF

From an office file (keeps its layout):

```sh
soffice --headless --convert-to pdf --outdir "$TMPDIR" "/abs/path/file.docx"   # also .xlsx, .pptx, .odt, .rtf, .txt
```

From text you write: write Markdown, make a docx with pandoc, then a PDF
with LibreOffice (pandoc cannot write PDF here):

```sh
pandoc "$TMPDIR/letter.md" -o "$TMPDIR/letter.docx"                    # add --reference-doc=firm.docx for the firm's style
soffice --headless --convert-to pdf --outdir "$TMPDIR" "$TMPDIR/letter.docx"
```

From images (scans, photos): `tesseract page.png "$TMPDIR/page" pdf` makes a
searchable one-page PDF per image; join them with `pdfunite`.

`soffice` runs one call at a time; wait for it to finish before the next.

## Size

There is no tool here that shrinks images inside a PDF. `qpdf --object-streams=generate --recompress-flate --compression-level=9 in.pdf "$TMPDIR/smaller.pdf"`
saves a little on text-heavy files. If the user needs a much smaller file,
say so; do not promise it.

## Check

Before you save, every time:

1. `pdfinfo "$TMPDIR/out.pdf"`: the page count is what you expect, and it
   opens without errors.
2. `pdftotext -layout -f 1 -l 1 "$TMPDIR/out.pdf" -`: the text is there
   (for filled forms, the values are there).
3. Render the pages you changed and look at them with `read`
   (`pdftoppm -png -r 60 -f N -l N ...`). For a merge, look at the first page of
   each part; for a rotation, the rotated pages.

## Save

Put the checked PDF in the user's folder with the `save` tool, under a new
name: `from` is its full path in `$TMPDIR`, `path` the destination, for example
`/abs/path/Contract - full set.pdf`. In ask mode the user is asked to approve
it first; if they decline, the file was not saved: tell them, do not retry.

Older Desk without a `save` tool: `cp "$TMPDIR/merged.pdf" "/abs/path/..."` in
the shell. If that fails with "Read-only file system" or "Permission denied",
tell the user the file is ready at its full `$TMPDIR` path and could not be
saved. Text you extracted can always be saved with `write` as a .txt or .md file.

Then tell the user in one or two lines what you made and where it was saved.
