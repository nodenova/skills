# Tracked changes and comments

The snippets assume the unpacked folder `$W/x` from the steps in `word-xml.md`.
Every shell call starts fresh: begin each with `S=<skill directory>; W="$TMPDIR/job1";`.

## Ids and dates

Each `w:id` of a change or comment must be unique in the document. Use
numbers above any already in use:

```sh
grep -o 'w:id="[0-9]*"' "$W/x/word/document.xml" | sort -t'"' -k2 -n | tail -1
```

Use today's date in `w:date` (`2026-01-31T00:00:00Z`) and the author name the
user wants (default `NodeNova Desk`).

## Mark a change (redline)

Wrap the old runs in `<w:del>` and the new runs in `<w:ins>`. Deleted text goes
in `<w:delText>`, not `<w:t>`. Keep the run's `<w:rPr>` in both.

```xml
<w:del w:id="901" w:author="NodeNova Desk" w:date="2026-01-31T00:00:00Z"><w:r><w:rPr><w:b/></w:rPr><w:delText xml:space="preserve">12%</w:delText></w:r></w:del><w:ins w:id="902" w:author="NodeNova Desk" w:date="2026-01-31T00:00:00Z"><w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">15%</w:t></w:r></w:ins>
```

- Mark only the words that change, not the whole sentence.
- A new paragraph: put `<w:ins>` around its runs and add
  `<w:rPr><w:ins w:id=".." w:author=".." w:date=".."/></w:rPr>` inside its
  `<w:pPr>` (marks the paragraph mark as inserted).
- A deleted paragraph: `<w:del>` around its runs, and
  `<w:rPr><w:del .../></w:rPr>` inside its `<w:pPr>`.

Check with `pandoc --track-changes=all -t markdown "$W/out.docx"`: insertions
show as `[...]{.insertion ...}`, deletions as `[...]{.deletion ...}`.

## Accept all changes

```sh
python3 "$S/scripts/docx_accept.py" "$W/x/word/document.xml"
```

It drops deleted text and moved-from text, keeps inserted text without the
marks, and removes formatting-change records. It prints how many marks are
left (should be 0). Run it on each header, footer and footnotes part that has
changes, then pack. To reject all changes, ask the user first; it is rarely
what they want.

## Add a comment

Mark the commented text in the part, then add the comment.

```xml
<w:commentRangeStart w:id="903"/><w:r><w:t>Revenue grew</w:t></w:r><w:commentRangeEnd w:id="903"/><w:r><w:commentReference w:id="903"/></w:r>
```

If `word/comments.xml` exists, add the comment before `</w:comments>`:

```xml
<w:comment w:id="903" w:author="NodeNova Desk" w:date="2026-01-31T00:00:00Z" w:initials="ND"><w:p><w:r><w:t>Check against the ledger.</w:t></w:r></w:p></w:comment>
```

If it does not exist, create it and register it (pack refuses the file
otherwise):

```sh
cat > "$W/x/word/comments.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:comment w:id="903" w:author="NodeNova Desk" w:date="2026-01-31T00:00:00Z" w:initials="ND"><w:p><w:r><w:t>Check against the ledger.</w:t></w:r></w:p></w:comment></w:comments>
EOF
python3 "$S/scripts/ooxml.py" replace "$W/x/word/_rels/document.xml.rels" '</Relationships>' \
  '<Relationship Id="rIdNN903" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="comments.xml"/></Relationships>'
python3 "$S/scripts/ooxml.py" replace "$W/x/[Content_Types].xml" '</Types>' \
  '<Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/></Types>'
```

The relationship `Id` must be new in that file.

## Reply to or resolve comments

Replies and "resolved" live in `word/commentsExtended.xml` (Word 2013+). Read
them with `pandoc --track-changes=all`. Adding replies is not covered here;
add a new comment on the same text instead, starting with "Re:".
