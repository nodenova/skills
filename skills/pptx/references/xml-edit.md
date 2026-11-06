# Editing slide XML by hand

Use this only for what `pptx_replace_text.py` cannot do. Each shell call
starts fresh: begin each with `S=<skill directory>; W="$TMPDIR/job1";`.

```sh
S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W"
python3 "$S/scripts/ooxml.py" unpack "/abs/path/deck.pptx" "$W/x"
grep -o '.\{0,300\}Revenue grew.\{0,300\}' "$W/x/ppt/slides/slide2.xml"
```

Take the slide's part from the outline. Slide XML is often one long line; do
not open it with `read`. Replace with OLD copied exactly from that output; it
changes the part only if OLD occurs exactly once (`--all` for every
occurrence). On a miss the error shows the closest text. The first argument
is an unpacked XML part, never the .pptx:

```sh
S=<skill directory>; W="$TMPDIR/job1"
python3 "$S/scripts/ooxml.py" replace "$W/x/ppt/slides/slide2.xml" '<a:t>12%</a:t>' '<a:t>15%</a:t>'
python3 "$S/scripts/ooxml.py" pack "/abs/path/deck.pptx" "$W/x" "$W/out.pptx"
```

When OLD or NEW has quotes of both kinds, write them to files with a quoted
heredoc and pass `"@$W/old.txt" "@$W/new.txt"`. `pack` copies every untouched
part from the original and checks the parts you changed: well-formed XML,
valid against the Office XML schema, relationships and content types in
order. It reports only problems your change added. On a problem it writes
nothing: fix it and pack again. "changed:" must list only the parts you meant.

- Escape `&` as `&amp;`, `<` as `&lt;`, `>` as `&gt;` in new text. Never put a
  line break character in `<a:t>`.
- A new bullet: copy the neighbouring `<a:p>...</a:p>` and change its text.
- A picture: find its file in `ppt/slides/_rels/slideN.xml.rels`
  (`../media/image3.png`) and overwrite it in `$W/x/ppt/media/` with an image
  of the same type and shape, after checking no other slide uses it
  (`grep -l image3.png "$W"/x/ppt/slides/_rels/*`).
