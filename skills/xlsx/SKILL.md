---
name: xlsx
description: Read, edit, create or convert Excel workbooks (.xlsx, .xlsm, .csv) in NodeNova Desk. Use for any task that opens, changes or produces a spreadsheet - reading sheets and formulas, changing cells, adding rows or formulas, checking totals, finding formula errors, a new workbook from data, CSV to xlsx, or a sheet to PDF. Not for Word documents, slides or PDFs.
---

# Excel workbooks (.xlsx)

A .xlsx is a zip of XML parts. `xl/workbook.xml` lists the sheets; each sheet
is `xl/worksheets/sheetN.xml`, but N is not the tab order (the scripts map
sheet names to parts). Shared text is in `xl/sharedStrings.xml`, formats in
`xl/styles.xml`.

**Skill folder.** This skill's scripts are in its `scripts/` folder, and its
longer guides are in `references/`. The folder's full path is printed at the
end of this text ("Skill directory"). Below, `S` is that path: start each
shell command with `S=<skill directory>;`. Read a guide with `cat "$S/references/<name>"`.

## Rules

1. **Never save a user's workbook through LibreOffice.** It rebuilds the whole
   file and loses formatting, names and macros. Use it only to read, to check,
   or to make a new file. To change a .xlsx, edit only the XML that needs it.
2. **Work in `$TMPDIR`.** Unpacked parts and drafts go there, never in the
   user's folder. `read` opens files there by full path.
3. **Stored results go stale.** A .xlsx keeps each formula's last result. After
   you change an input, those results are old (LibreOffice shows the old ones
   too) until the workbook recalculates. Always run `xlsx_check.py` to see
   the real results, and set the workbook to recalculate when opened.
4. **Change only what was asked**, and save only a file that passed the checks,
   with the `save` tool.

**Password-protected files** are not zips: `ooxml.py unpack` fails with
"File is not a zip file" and `file <path>` says "CDFV2 Encrypted". They
cannot be read or changed here; ask the user for an unprotected copy.

## Read

```sh
S=<skill directory>; python3 "$S/scripts/xlsx_dump.py" "/abs/path/book.xlsx" > "$TMPDIR/book.txt"; head -100 "$TMPDIR/book.txt"
```

Every non-empty cell, sheet by sheet: `B4  1200` for a value,
`D9  =SUM(D2:D8)  -> 5400` for a formula and its stored result. `grep` the
file for a large workbook. Dates show as day numbers (45658 is 2025-01-01).
To see values as the user sees them (dates, currency, %), export every sheet:

```sh
soffice --headless --convert-to "csv:Text - txt - csv (StarCalc):44,34,UTF8,1,,0,false,true,false,false,false,-1" \
  --outdir "$TMPDIR/csv" "/abs/path/book.xlsx"     # one <book>-<sheet>.csv per sheet
```

To see the layout, `soffice --headless --convert-to pdf --outdir "$TMPDIR" <file>`,
then `pdftoppm -png -r 80 -f 1 -l 1 "$TMPDIR/<name>.pdf" "$TMPDIR/page"` and
`read` the PNG. `soffice` runs one call at a time.

## Edit

```sh
S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W"
python3 "$S/scripts/ooxml.py" unpack "/abs/path/book.xlsx" "$W/x"
python3 "$S/scripts/xlsx_dump.py" "/abs/path/book.xlsx" > "$W/before.txt"
python3 "$S/scripts/xlsx_dump.py" "/abs/path/book.xlsx" "Budget" B5 D12
```

The last line prints the sheet's part (e.g. `xl/worksheets/sheet2.xml`) and
the exact XML of each cell, or of its row when the cell does not exist yet.
Sheet XML is often one long line; do not open it with `read`.

Replace with OLD copied exactly; it changes the part only if OLD occurs once.
Keep the cell's `s="..."` (its format):

```sh
python3 "$S/scripts/ooxml.py" replace "$W/x/xl/worksheets/sheet2.xml" \
  '<c r="B5" s="3"><v>1200</v></c>' '<c r="B5" s="3"><v>1250.5</v></c>'
```

| Cell | XML |
|---|---|
| Number | `<c r="B5" s="3"><v>1250.5</v></c>` (no thousands separator, `.` for decimals) |
| Text | `<c r="B5" s="3" t="inlineStr"><is><t>Paid in full</t></is></c>` |
| Formula | `<c r="D12" s="4"><f>SUM(D2:D11)</f></c>` (no `=`, no `<v>`) |
| True/false | `<c r="E2" t="b"><v>1</v></c>` |

Before adding cells or rows, formulas across sheets, or removing a formula,
read `cat "$S/references/cells.md"`.

Then turn on recalculation when opened: find the tag with
`grep -o '<calcPr[^>]*>' "$W/x/xl/workbook.xml"` and replace it with the same
tag plus ` fullCalcOnLoad="1"` (e.g. `<calcPr calcId="191029" fullCalcOnLoad="1"/>`).
If there is no `<calcPr>`, insert `<calcPr fullCalcOnLoad="1"/>` right after
`</definedNames>`, or after `</sheets>` when there are no defined names.

Pack:

```sh
python3 "$S/scripts/ooxml.py" pack "/abs/path/book.xlsx" "$W/x" "$W/out.xlsx"
```

`pack` copies every untouched part from the original and checks the parts you
changed: well-formed XML, valid against the Office XML schema, relationships
and content types in order. It reports only problems your change added. On a
problem it writes nothing: fix it and pack again. "changed:" must list only
the parts you meant to touch. A .xlsm keeps its macros; keep the name.

## Create

Write a JSON spec and build the workbook; the spec format is in
`cat "$S/references/new-workbook.md"`:

```sh
python3 "$S/scripts/xlsx_new.py" "$W/spec.json" "$W/out.xlsx"
```

To turn a CSV into a workbook as is: `soffice --headless --convert-to xlsx --outdir "$W" "/abs/path/data.csv"`
(it guesses types: leading zeros and long numbers can change; use the spec
when that matters).

## Convert

```sh
soffice --headless --convert-to pdf --outdir "$W" "/abs/path/book.xlsx"   # every sheet -> PDF
soffice --headless --convert-to xlsx --outdir "$W" "/abs/path/book.xls"   # old .xls -> new .xlsx copy
```

## Check

1. `pack` passed (for a new file: `python3 "$S/scripts/ooxml.py" validate "$W/out.xlsx"`).
2. Real results, no errors: `python3 "$S/scripts/xlsx_check.py" "$W/out.xlsx"`.
   It recalculates a scratch copy and lists every formula with its fresh
   result, then the errors (`#REF!`, `#DIV/0!`, `#NAME?`, `#VALUE!`, `#N/A`,
   `Err:5xx`). Fix every error you caused; check the totals the user cares
   about. Errors that were already there: mention them, do not fix unasked.
3. Only the intended cells changed:
   `python3 "$S/scripts/xlsx_dump.py" "$W/out.xlsx" > "$W/after.txt"; diff "$W/before.txt" "$W/after.txt"`
   (stored formula results still show the old numbers here; step 2 has the new ones).

## Save

Put the checked file in the user's folder with the `save` tool:
`from` is the file's full path (`echo "$W/out.xlsx"` prints it), `path` is
where it goes, for example `/abs/path/book.xlsx` when the user asked to
change that file, or `/abs/path/book (edited).xlsx` for a new one next to it.
Replace the original only when the user asked to change that file.

`save` checks an Office file again in Desk itself and refuses a damaged one;
its answer lists the parts that changed, which must be only the ones you meant
to touch. In ask mode the user is asked to approve it first; if they decline,
the file was not saved: tell them, do not retry.

Older Desk without a `save` tool: `cp "$W/out.xlsx" "/abs/path/..."` in the
shell. If that fails with "Read-only file system" or "Permission denied", tell
the user the file is ready at its full `$TMPDIR` path and could not be saved. (A .csv is text: `write` can save that.)

Then tell the user in one or two lines what changed, the key results from
`xlsx_check.py`, and where it was saved.
