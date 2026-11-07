---
name: docx
description: Read, edit, create or convert Word documents (.docx, .dotx) in NodeNova Desk. Use for any task that opens, changes or produces a Word file - find and replace, rewording a clause, tracked changes, comments, accepting changes, tables, headers and footers (text on every page), swapping a picture or logo, a new report, memo or letter from text, or a docx to PDF. Not for PDFs, spreadsheets or slides.
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

To see the layout, render a page and `read` the image (one `soffice` at a time;
if `soffice` is not found, skip the render and verify with `pandoc` and `docx_images.py list`):

```sh
W="$TMPDIR/job1"; mkdir -p "$W"; soffice --headless --convert-to pdf --outdir "$W" "/abs/path/file.docx"
pdftoppm -png -r 80 -f 1 -l 1 "$W/file.pdf" "$W/page"   # then read $W/page-1.png
```

## Edit

Measure, change, then count. Never print a part to look at it:
`word/document.xml` is often one line of hundreds of KB, and printing it
(`unzip -p`, `cat`, `head`) fills your context and ends the task. Count with
`grep -c`, `grep -o ... | sort | uniq -c`, or a script that prints numbers.

**One or a few places** (a sentence, a heading, a cell): these scripts find
text by its words, even when Word split it across runs, and write OUT through
the checked pack:

```sh
S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W"
python3 "$S/scripts/docx_find.py" "/abs/path/file.docx" "Invitation to Tender"
python3 "$S/scripts/docx_format.py" "/abs/path/file.docx" "$W/out.docx" --paragraph-containing "Invitation to Tender" --color FF0000
python3 "$S/scripts/docx_replace_text.py" "/abs/path/file.docx" "$W/out.docx" "within 30 days" "within 14 days"
```

- `docx_find.py FILE TEXT` lists the paragraphs with TEXT: number, text, each
  run with its formatting. FILE may also be an unpacked folder or one part.
  TEXT is one phrase from one paragraph. A line with tabs in `read` output is
  a table row: each cell is its own paragraph, so search one cell's text.
- `docx_format.py IN OUT PICK FORMAT...`. PICK: `--paragraph N` (number from
  `docx_find.py`; `--paragraph 3,7,12` for several) or
  `--paragraph-containing TEXT` with `--occurrence K` or `--all` when several
  paragraphs match. FORMAT: `--color 8B0000|darkred`, `--bold|--no-bold`,
  `--italic|--no-italic`, `--underline|--no-underline`, `--size 14`,
  `--highlight yellow`, `--font Arial`. All runs of the paragraph change, and
  the old colour (theme colour too) is replaced. It prints how many paragraphs
  and runs changed: check that number against what you meant.
- `docx_replace_text.py IN OUT OLD NEW [--all]`: plain text, no XML. NEW takes
  the formatting of the run where OLD starts.
- Header or footer text: `--part word/header1.xml` (`docx_find.py FILE TEXT word/header1.xml`).
- `docx_header.py IN OUT --text TEXT [--footer] [--align left|center|right] [--replace] [--type default|first|even]`:
  puts TEXT in the header (footer) of every page, creating it where missing;
  pictures and page numbers in an existing header stay.
- Pictures and logos are not text, so `docx_find.py` never finds them:
  `docx_images.py list FILE` shows each picture (image file, pixel and shown
  size, header/footer/body place, alt text, nearby text) and
  `docx_images.py replace IN OUT --image word/media/image1.jpeg --with NEW.png [--fit]`
  swaps one. Never print an image; use `file`, `identify` or the list
  command. No image to use (an emoji, a new logo)? `cat "$S/references/pictures-and-headers.md"`.
- A second edit starts from the first result: IN `"$W/out.docx"`, OUT `"$W/out2.docx"`.
- Errors are one line, `ERROR: ...`. If TEXT or OLD is not found, it shows the
  closest text: copy from it, not from memory.

**The whole document, or a pattern** (every paragraph, every heading, every
table, a word in hundreds of places): one short Python script over the XML,
not one command per paragraph. Unpack and measure:

```sh
S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W"
python3 "$S/scripts/ooxml.py" unpack "/abs/path/file.docx" "$W/x"
D="$W/x/word/document.xml"; for p in '<w:p[ >]' '<w:r[ >]' '<w:t[ >]' '<w:color ' '<w:tbl>'; do echo "$p $(grep -oE "$p" "$D" | wc -l)"; done; grep -oE '<w:color [^>]*>' "$D" | sort | uniq -c | sort -rn | head
```

Write the change as a script file (quoted heredoc, never `python3 -c`) that
reads the part, changes only what was asked, writes it back and prints counts.
A run's format is its `<w:rPr>`, the first child of `<w:r>`. Example, all text
dark red (`w:color` goes after `rStyle rFonts b bCs i iCs caps smallCaps strike
dstrike outline shadow emboss imprint noProof snapToGrid vanish webHidden` and
before every other element):

```sh
S=<skill directory>; W="$TMPDIR/job1"
cat > "$W/recolor.py" <<'PY'
import re, sys
path, color = sys.argv[1], sys.argv[2]
xml = open(path, encoding='utf-8', newline='').read()
BEFORE = set('rStyle rFonts b bCs i iCs caps smallCaps strike dstrike outline shadow emboss imprint noProof snapToGrid vanish webHidden'.split())
TAG = f'<w:color w:val="{color}"/>'
CHILD = re.compile(r'<w:(\w+)\b(?:[^>]*/>|[^>]*>.*?</w:\1>)', re.S)
counts = {'recoloured': 0, 'kept white': 0}

def with_color(inner):
    if 'w:val="FFFFFF"' in inner:
        counts['kept white'] += 1
        return inner
    counts['recoloured'] += 1
    if '<w:color ' in inner:
        return re.sub(r'<w:color [^>]*/>', TAG, inner)
    at = 0
    for m in CHILD.finditer(inner):
        if m.group(1) in BEFORE:
            at = m.end()
    return inner[:at] + TAG + inner[at:]

def run(m):
    head, body = m.group(1), m.group(2)
    if '<w:t' not in body:
        return m.group(0)
    rpr = re.match(r'<w:rPr>(.*?)</w:rPr>', body, re.S)
    if rpr:
        return f'{head}<w:rPr>{with_color(rpr.group(1))}</w:rPr>{body[rpr.end():]}</w:r>'
    return f'{head}<w:rPr>{with_color("")}</w:rPr>{body}</w:r>'

xml = re.sub(r'(<w:r(?: [^>]*)?>)(.*?)</w:r>', run, xml, flags=re.S)
open(path, 'w', encoding='utf-8', newline='').write(xml)
print(counts)
PY
python3 "$W/recolor.py" "$W/x/word/document.xml" 8B0000
python3 "$S/scripts/ooxml.py" pack "/abs/path/file.docx" "$W/x" "$W/out.docx"
```

Then count again in OUT and compare with what you meant (here: text runs
without `8B0000` should be only the white ones). A script's "done" or
"checks passed" says the file is valid, not that the change is complete.
White or light text on a dark fill (table headers) would become unreadable:
leave it and tell the user. Colours: dark red 8B0000, dark blue 00008B,
dark green 006400, red FF0000.

For new paragraphs, table rows, new pictures, tracked changes and comments,
edit the XML by hand: `cat "$S/references/word-xml.md"`,
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

1. `pack` or the script says "checks passed", "changed:" lists only the
   part you meant, and your own count shows every intended place changed (for a new file: `python3 "$S/scripts/ooxml.py" validate "$W/out.docx"`;
   pandoc output has a few schema slips Word accepts).
2. The text changed only where intended:
   `pandoc -t plain --track-changes=all "/abs/path/file.docx" > "$W/before.txt"; pandoc -t plain --track-changes=all "$W/out.docx" > "$W/after.txt"; diff "$W/before.txt" "$W/after.txt"`
3. It opens and looks right: render the changed page as in "Read" and look at
   it. If `soffice` makes no PDF, the file is broken; do not save it. If
   `soffice` is not found, skip this step: check the text diff in step 2 and
   `docx_images.py list "$W/out.docx"`, and say the layout was not looked at.

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
