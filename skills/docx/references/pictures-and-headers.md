# Pictures, logos and page headers (.docx)

## Find and swap a picture

```sh
S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W"
python3 "$S/scripts/docx_images.py" list "/abs/path/file.docx"
python3 "$S/scripts/docx_images.py" replace "/abs/path/file.docx" "$W/out.docx" --image word/media/image1.jpeg --with "/abs/path/new-logo.png" --fit
```

`list` prints one block per picture: where it is (`body, paragraph 12`, or
`default header`, `first footer`), the image file, its pixel size and file
size, the size it is shown at, its name and alt text and the text around it.
A logo is usually in a header (look at `default header` and `first header`).
The same image file can show in several places; `replace` changes all of them.

- Default keeps the shown size, so a wider or taller image is stretched. `--fit`
  keeps the new image's proportions inside the old box and drops any crop.
- A different format (jpeg to png) renames the part, follows it in the
  relationships and adds the content type. SVG is refused (convert to PNG).
- The check line "changed:" should list the image, `.rels` files and at most
  `[Content_Types].xml` and the page when `--fit` is used.
- Floating pictures keep their position; `--fit` changes only the size.

## Never dump binary or big XML

`unzip -p file.docx word/media/image1.jpeg`, `cat` on an image, or printing
`document.xml` (hundreds of KB) fills the context and the work stops. Use:
`file image.png`, `identify image.png` (if ImageMagick is installed),
`unzip -l file.docx` for names, `grep -o` with a small window for XML.

## A picture that does not exist yet (emoji, text logo)

Needs an image file. Options in this order:

1. The user attached an image: use it.
2. Plain text as a picture, if ImageMagick exists (`command -v magick convert`):
   `magick -background none -fill black -font Arial -pointsize 96 label:"NodeNova" "$W/logo.png"`
   (`convert` instead of `magick` on older installs). The font must contain
   every character; `magick -list font | grep -i font:` shows what exists.
3. Emoji need a colour emoji font (Apple Color Emoji, Noto Color Emoji), which
   offline machines usually lack, and ImageMagick often draws empty boxes. Do
   not pretend: tell the user the emoji cannot be drawn here and ask them to
   attach an image file (PNG preferred), then use `replace`.

Look at nothing you cannot see: there is no vision, so check the result with
`identify "$W/logo.png"` (size not tiny) and `docx_images.py list`.

## Header and footer text on every page

```sh
python3 "$S/scripts/docx_header.py" "/abs/path/file.docx" "$W/out.docx" --text "NodeNova" --align center
python3 "$S/scripts/docx_header.py" "$W/out.docx" "$W/out2.docx" --text "Page footer" --footer
```

- A section without a header gets a new `headerN.xml` (relationship, content
  type and `w:headerReference` in each section, including paragraph-level
  section breaks). A section that already has one keeps its pictures and
  fields and gets the text as one more paragraph (or in its empty paragraph).
- "Different first page" (`w:titlePg`) needs a first-page header and "different
  odd and even" (`w:evenAndOddHeaders` in settings) an even one; both are
  filled too. `--type default|first|even` fills only that kind.
- `--replace` swaps the existing text paragraphs by the new text, keeping
  their formatting; running the command again with the same text changes
  nothing. To reword a header later: `docx_replace_text.py IN OUT OLD NEW --part word/header1.xml`.
- Page numbers are fields, not text; leave them as they are.
