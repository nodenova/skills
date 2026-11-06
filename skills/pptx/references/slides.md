# Reorder, delete and duplicate slides

Each shell call starts fresh: begin each with `S=<skill directory>; W="$TMPDIR/job1";`
and work in the unpacked folder `$W/x` (unpack it as in `xml-edit.md`).

All three change `<p:sldIdLst>` in `ppt/presentation.xml`. See it with:

```sh
grep -o '<p:sldIdLst>.*</p:sldIdLst>' "$W/x/ppt/presentation.xml"
```

Each `<p:sldId id="257" r:id="rId3"/>` is one slide, in show order. `r:id`
points to a `<Relationship>` in `ppt/_rels/presentation.xml.rels` whose
`Target` is the slide part. `pptx_outline.py` prints both for every slide.

## Reorder

Replace the whole `<p:sldIdLst>...</p:sldIdLst>` with the same entries in the
new order. Copy each entry exactly.

## Delete

1. Remove the slide's `<p:sldId .../>` from `ppt/presentation.xml`.
2. Remove the `<Relationship>` with the same `Id` from
   `ppt/_rels/presentation.xml.rels`.

Leave the slide's own files in place.

## Duplicate

To copy slide part `slide2.xml` as a new `slide9.xml` (use a number not yet in
`ppt/slides/`):

```sh
cd "$W/x"
cp ppt/slides/slide2.xml ppt/slides/slide9.xml
sed 's#<Relationship [^>]*notesSlide[^>]*/>##g' ppt/slides/_rels/slide2.xml.rels > ppt/slides/_rels/slide9.xml.rels
python3 "$S/scripts/ooxml.py" replace "[Content_Types].xml" '</Types>' \
  '<Override PartName="/ppt/slides/slide9.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/></Types>'
python3 "$S/scripts/ooxml.py" replace ppt/_rels/presentation.xml.rels '</Relationships>' \
  '<Relationship Id="rIdNN9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide9.xml"/></Relationships>'
```

Then add `<p:sldId id="NEW" r:id="rIdNN9"/>` to `<p:sldIdLst>` where the copy
should appear (e.g. replace the entry before it with that entry plus the new
one). `NEW` is a number larger than every `id` in the list. The relationship
`Id` must be new in that `.rels` file.

The copy keeps the original's layout and pictures (it points to the same
image files, which is fine) but has no speaker notes. Change its text as in
SKILL.md.

A slide with a chart, a SmartArt diagram or an embedded object needs more:
those parts belong to one slide each, so copy the chart part (and its
`.rels` and embedded workbook) under new names, add their content types, and
point the copy's relationships at them. If that is more than the task needs,
duplicate a slide without them, or ask the user.

`pack` checks the wiring: a missing content type, a relationship to a part
that does not exist, or a duplicate `Id` stops it.
