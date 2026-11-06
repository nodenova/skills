# Cells, rows and formulas in sheet XML

Use this when `xlsx_set.py` cannot do the edit. Each step is its own shell
call, starting `S=<skill directory>; W="$TMPDIR/job1";`.

## By hand: unpack, replace, recalculate, pack

```sh
S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W"
python3 "$S/scripts/ooxml.py" unpack "/abs/path/book.xlsx" "$W/x"
python3 "$S/scripts/xlsx_dump.py" "/abs/path/book.xlsx" "Budget" B5 D12
```

The last line prints the sheet's part (e.g. `xl/worksheets/sheet2.xml`) and
the exact XML of each cell, or of its row when the cell does not exist yet.
Replace with OLD copied exactly; it changes the part only if OLD occurs once
(on a miss the error shows the closest text). Keep the cell's `s="..."`. With
quotes of both kinds, put OLD and NEW in files with a quoted heredoc and pass
`"@$W/old.txt" "@$W/new.txt"`:

```sh
S=<skill directory>; W="$TMPDIR/job1"
python3 "$S/scripts/ooxml.py" replace "$W/x/xl/worksheets/sheet2.xml" \
  '<c r="B5" s="3"><v>1200</v></c>' '<c r="B5" s="3"><v>1250.5</v></c>'
```

| Cell | XML |
|---|---|
| Number | `<c r="B5" s="3"><v>1250.5</v></c>` (no thousands separator, `.` for decimals) |
| Text | `<c r="B5" s="3" t="inlineStr"><is><t>Paid in full</t></is></c>` |
| Formula | `<c r="D12" s="4"><f>SUM(D2:D11)</f></c>` (no `=`, no `<v>`) |
| True/false | `<c r="E2" t="b"><v>1</v></c>` |

Then turn on recalculation when opened: find the tag with
`grep -o '<calcPr[^>]*>' "$W/x/xl/workbook.xml"` and replace it with the same
tag plus ` fullCalcOnLoad="1"` (e.g. `<calcPr calcId="191029" fullCalcOnLoad="1"/>`).
If there is no `<calcPr>`, insert `<calcPr fullCalcOnLoad="1"/>` right after
`</definedNames>`, or after `</sheets>` when there are no defined names. Then
`python3 "$S/scripts/ooxml.py" pack "/abs/path/book.xlsx" "$W/x" "$W/out.xlsx"`.

## Cell types

A sheet's data is `<sheetData>`: rows `<row r="5">`, and in each row cells
`<c r="B5">`. A cell's type is its `t` attribute, its format its `s`
attribute (an index into `cellXfs` in `xl/styles.xml`), its value `<v>`, its
formula `<f>`.

| `t` | Meaning | Value |
|---|---|---|
| none or `n` | number | `<v>1250.5</v>` |
| `s` | shared text | `<v>7</v>` is entry 7 of `xl/sharedStrings.xml` |
| `inlineStr` | text in the cell | `<is><t>Paid</t></is>` |
| `str` | text result of a formula | `<f>..</f><v>text</v>` |
| `b` | true/false | `<v>1</v>` / `<v>0</v>` |
| `e` | error | `<v>#DIV/0!</v>` |

## Text

Write new text as `inlineStr`. Do not change an entry of `sharedStrings.xml`:
one entry can be used by many cells, so the change would show up elsewhere.
When you turn a shared-text cell into an `inlineStr` cell, drop its `t="s"`
and `<v>`.

Escape `&` as `&amp;`, `<` as `&lt;`, `>` as `&gt;` in text and formulas.

## Formulas

- Written without `=`: `<f>SUM(D2:D11)</f>`. Leave out `<v>`; the workbook
  recalculates (set `fullCalcOnLoad`, see SKILL.md) and `xlsx_check.py` shows
  the result.
- Text inside a formula keeps plain quotes: `<f>IF(A2&gt;0,"yes","no")</f>`.
- Another sheet: `'Sheet name'!B4` (quotes when the name has spaces or
  symbols). Function names in English with `,` between arguments, whatever
  the user's locale.
- `<f t="shared" ref="D2:D20" si="0">B2*C2</f>` defines a formula shared down
  a range; the other cells have `<f t="shared" si="0"/>`. To change one cell
  of a shared range, give that cell its own full `<f>`; to change the master
  cell, keep the `ref` and `si`.
- Array formulas have `t="array"`; leave them alone unless asked.

## Adding cells and rows

- Cells in a row are in column order: A, B, ..., Z, AA, AB. Insert a new cell
  at its place in the row.
- Rows are in number order. A new row: `<row r="13"><c r="A13" ...>...</c></row>`,
  inserted after `</row>` of row 12 (or the nearest lower row).
- Give a new cell the format of the cell above it (copy its `s="..."`).
- If the used range grows, update `<dimension ref="A1:F13"/>` near the top of
  the sheet.
- A table (`xl/tables/tableN.xml`) has its own `ref="A1:F12"`; extend it when
  you add a row to the table.
- Do not insert rows that push existing ones down: every reference below and
  in other sheets, names, charts and formats would need to change. Add rows
  at the end of the data, or ask the user.

## Removing a formula

When a formula cell becomes a plain value (or is emptied), delete the
calculation chain so Excel rebuilds it; otherwise Excel reports damage:

1. `mv "$W/x/xl/calcChain.xml" "$W/calcChain.removed"` (moves it out of the
   unpacked folder; pack then leaves it out),
2. remove its `<Relationship ... Target="calcChain.xml"/>` from
   `xl/_rels/workbook.xml.rels`,
3. remove its `<Override PartName="/xl/calcChain.xml" .../>` from
   `[Content_Types].xml`.

`pack` refuses the file if one of the three is left behind.

## Number formats

A cell's display format comes from `s`. To format a new cell like its
neighbours, copy their `s`. Making a new format means editing `xl/styles.xml`
(`numFmts` and `cellXfs`); only do it when no existing `s` fits.
