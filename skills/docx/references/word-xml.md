# Writing Word XML

Use this only for what `docx_format.py` and `docx_replace_text.py` cannot do:
new paragraphs, table rows, pictures, tracked changes, comments.

## Steps

Each step is its own shell call, so each starts with the same line
(`S` is the skill directory, printed at the end of SKILL.md):

```sh
S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W"
python3 "$S/scripts/ooxml.py" unpack "/abs/path/file.docx" "$W/x"
python3 "$S/scripts/docx_find.py" "$W/x" "late payment" --xml      # exact XML of the paragraph
```

Replace OLD with NEW in one part. OLD must be copied exactly from the
`--xml` output and must occur once (`--all` changes every occurrence). If it
is not found, the error shows the closest text and the first difference. With
quotes of both kinds, or long XML, write OLD and NEW to files with a quoted
heredoc and pass `"@$W/old.txt" "@$W/new.txt"`:

```sh
S=<skill directory>; W="$TMPDIR/job1"
cat > "$W/old.txt" <<'EOF'
<w:t>within 30 days</w:t>
EOF
cat > "$W/new.txt" <<'EOF'
<w:t>within 14 days</w:t>
EOF
python3 "$S/scripts/ooxml.py" replace "$W/x/word/document.xml" "@$W/old.txt" "@$W/new.txt"
python3 "$S/scripts/ooxml.py" pack "/abs/path/file.docx" "$W/x" "$W/out.docx"
```

`replace` takes an unpacked XML part (a file inside `$W/x`), never the .docx.
For a larger edit, write a Python script file in `$W` with a quoted heredoc
and run it on the part; do not use `python3 -c`.

`pack` copies every untouched part from the original and checks the parts you
changed: well-formed XML, valid against the Office XML schema, relationships
and content types in order. It reports only problems your change added. On a
problem it writes nothing and says what is wrong: fix it and pack again.

## Rules for the XML

Rules for the XML you put into `word/document.xml` (and headers, footers,
footnotes). `ooxml.py pack` rejects XML that breaks the schema; these rules
keep you from getting there.

## Text

- Escape `&` as `&amp;`, `<` as `&lt;`, `>` as `&gt;` in text.
- A `<w:t>` whose text starts or ends with a space needs
  `<w:t xml:space="preserve">`.
- Never put a line break character inside `<w:t>`. A line break within a
  paragraph is its own run: `<w:r><w:br/></w:r>`. A tab is `<w:r><w:tab/></w:r>`.
- Curly quotes, dashes and accents are fine as plain UTF-8.

## Runs and formatting

A paragraph `<w:p>` holds runs `<w:r>`. A run's format is in its `<w:rPr>`,
which comes first in the run:

```xml
<w:r><w:rPr><w:b/><w:i/></w:rPr><w:t>bold italic</w:t></w:r>
```

- To change text but keep its look, keep the run's `<w:rPr>` as it was.
- When a phrase spans runs, put the new text in the first run and drop the
  other runs of the phrase.
- Inside `<w:rPr>`, write elements in this order:
  `rStyle, rFonts, b, i, caps, strike, color, sz, highlight, u, vertAlign`.
  Inside `<w:pPr>`: `pStyle, keepNext, numPr, spacing, ind, jc, rPr`. If
  `pack` reports "This element is not expected", the order is wrong: it
  lists what it expected there.
- Prefer the document's own styles to direct formatting: a heading is
  `<w:pPr><w:pStyle w:val="Heading2"/></w:pPr>` with the style id from
  `word/styles.xml` (`grep -o 'w:styleId="[^"]*"' word/styles.xml`).

## Paragraphs

- `<w:pPr>` comes first in the paragraph; `<w:pStyle>` comes first in `<w:pPr>`.
- To add a paragraph, copy a neighbouring paragraph's full XML (so it gets the
  same style and numbering) and change its text. Insert it right after the
  `</w:p>` of the paragraph it should follow.
- Remove `w14:paraId="..."` and `w14:textId="..."` from the copy; two
  paragraphs must not share them.
- Do not copy a paragraph that holds a bookmark (`w:bookmarkStart`), a
  comment anchor (`w:commentRangeStart`), a field (`w:fldChar`, a table of
  contents entry) or a picture without changing it: their ids and names must
  stay unique. Pick a plain neighbour, or drop those elements from the copy
  (a picture needs a new `wp:docPr id` and, for a new image, its own
  relationship).
- A numbered or bulleted item has `<w:numPr>` in its `<w:pPr>`; copy an
  existing item of the same list to stay in that list.
- The last element of `<w:body>` is `<w:sectPr>` (page size, margins). Keep
  new content before it.

## Tables

`<w:tbl>` holds `<w:tblPr>`, `<w:tblGrid>`, then rows `<w:tr>`; a row holds
cells `<w:tc>`; every cell holds at least one `<w:p>` (an empty cell is
`<w:tc><w:p/></w:tc>` plus its `<w:tcPr>`).

- To add a row, copy a whole `<w:tr>...</w:tr>` of the same table and change
  the cell text. Keep the number of cells.
- To change a cell, edit the text in its paragraph; keep `<w:tcPr>`.

## Pictures

Find the picture in `word/media/` (`unzip -l file.docx | grep media`). To
replace it, overwrite that file in the unpacked folder with an image of the
same type (png for png) and shape; Word keeps the size set in the document.
A new picture needs a relationship, a content type and drawing XML; copy an
existing picture's `<w:drawing>` and its relationship if the document has one,
and use a new `r:embed` id that you add to `word/_rels/document.xml.rels`.

## Headers, footers, footnotes

Each is its own part: `word/header1.xml`, `word/footer2.xml`,
`word/footnotes.xml`. Which header a section uses is in its `<w:sectPr>`
(`<w:headerReference w:type="default" r:id="rId8"/>`, resolved in
`word/_rels/document.xml.rels`). Edit them the same way as the body.

## Fields

Page numbers, dates and cross-references are fields
(`<w:fldSimple w:instr="PAGE">` or `<w:fldChar>` runs). Do not type over their
result; change the instruction or leave them alone.
