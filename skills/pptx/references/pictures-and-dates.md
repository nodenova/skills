# Pictures, logos and dates (.pptx)

## Find and swap a picture

```sh
S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W"
python3 "$S/scripts/pptx_images.py" list "/abs/path/deck.pptx"
python3 "$S/scripts/pptx_images.py" replace "/abs/path/deck.pptx" "$W/out.pptx" --image ppt/media/image1.png --with "/abs/path/new.png" --fit
```

`list` prints each picture on slides, layouts and masters: place, image file,
pixel size, shown size, name, alt text, slide text nearby. A logo that is on
every slide usually lives on the layout or master and is listed once there;
`replace` changes every place that shows the image file.

- Default keeps position and size. `--fit` keeps the new image's proportions
  inside the old box, centred, and drops any crop.
- A different format renames the part, updates relationships and adds the
  content type. SVG is refused (convert to PNG).
- A picture used as a shape fill or background is listed as `picture fill`;
  its size is not known, so `--fit` leaves it.
- Never print an image file or a slide XML whole to the terminal: use `file`,
  `identify` (if installed) and the list command.
- No image for what the user asked (an emoji, a drawn logo)? ImageMagick
  (`magick` or `convert`, check with `command -v`) can draw text to PNG with
  `magick -background none -fill black -font Arial -pointsize 96 label:"Text" "$W/logo.png"`
  if the font has every glyph. Emoji need a colour emoji font that offline
  machines usually lack. Then say so and ask the user to attach an image.

## Dates and footers

Footer, date and slide-number text sit in placeholders
(`<p:ph type="dt|ftr|sldNum"/>`) on the slide, repeated from the layout and
master. `pptx_outline.py FILE` marks them on slides, `--layouts` lists them on
layouts and masters.

- A fixed date is plain text: `pptx_replace_text.py IN OUT "11/3/2026" "11/6/2026" --all`.
- An automatic date is a field `{datetime1: 11/3/2026}`: the stored text is a
  cache and PowerPoint shows today's date on opening. If the user wants a
  fixed date, add `--fixed` (turns those fields into plain text). If they want
  the date to update itself, no change is needed.
- Layouts and the master (what new slides start from): add `--all-parts`.
  Changing only slides leaves new slides with the old date.
- Several formats of the same date (`11/3/2026`, `3 November 2026`) are
  separate texts; search the outline for each.
