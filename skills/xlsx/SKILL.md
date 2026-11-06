---
name: xlsx
description: Read, edit, create or convert Excel workbooks (.xlsx, .xlsm, .csv) in NodeNova Desk. Use for any task that opens, changes or produces a spreadsheet - reading sheets and formulas, changing cells, adding rows or formulas, checking totals, finding formula errors, a new workbook from data, CSV to xlsx, or a sheet to PDF. Not for Word documents, slides or PDFs.
---

# Excel workbooks (.xlsx)

A .xlsx is a zip of XML parts. `xl/workbook.xml` lists the sheets; each sheet
is `xl/worksheets/sheetN.xml`, but N is not the tab order (the scripts map
sheet names to parts). Shared text is in `xl/sharedStrings.xml`, formats in
`xl/styles.xml`.

**Every shell call starts fresh.** Variables, `cd` and functions from an
earlier call are gone. Start each command with
`S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W";` (`S` is the "Skill
directory" printed at the end of this text) and use full paths. Never run
`python3 -c "..."` with text from the file inside the quotes; write a script
file with a quoted heredoc and run that. Guides are in `$S/references/`.

## Rules

1. **Never save a user's workbook through LibreOffice or openpyxl.** They
   rebuild the whole file and lose formatting, names and macros; use them only
   to read, check, or make a new file. Edit a .xlsx with the scripts below.
2. **Work in `$TMPDIR`**, never in the user's folder.
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

To change cells, use `xlsx_set.py`. You never write XML, and it keeps each
cell's format, adds missing rows and cells in order, updates the sheet's
dimension and turns on recalculation when the file opens:

```sh
S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W"
python3 "$S/scripts/xlsx_dump.py" "/abs/path/book.xlsx" > "$W/before.txt"; head -100 "$W/before.txt"
python3 "$S/scripts/xlsx_set.py" "/abs/path/book.xlsx" "$W/out.xlsx" "Budget" B5 1250.5 A9 "Paid in full" D12 "=SUM(D2:D11)"
```

- `xlsx_set.py IN OUT SHEET CELL VALUE [CELL VALUE ...]`. VALUE: a number,
  TRUE/FALSE, a formula starting with `=` (English names, `,` between
  arguments), text, or `""` to empty the cell. `--text` keeps every VALUE as
  text (codes like 0012). Dates are day numbers.
- It writes OUT through the checked pack ("changed:" must list only the sheet
  part and `xl/workbook.xml`). Errors are one line, `ERROR: ...`; fix the
  command, do not fall back to `python3 -c`.
- It refuses cells inside a shared or array formula. For those, other styles,
  tables, or removing many formulas, edit the XML by hand:
  `cat "$S/references/cells.md"`.
- A second edit starts from the first result: IN `"$W/out.xlsx"`, OUT `"$W/out2.xlsx"`.
  A .xlsm keeps its macros; keep the extension.

## Create

Write a JSON spec and build the workbook; the spec format is in
`cat "$S/references/new-workbook.md"`:

```sh
S=<skill directory>; W="$TMPDIR/job1"; mkdir -p "$W"
python3 "$S/scripts/xlsx_new.py" "$W/spec.json" "$W/out.xlsx"
```

To turn a CSV into a workbook as is: `soffice --headless --convert-to xlsx --outdir "$W" "/abs/path/data.csv"`
(it guesses types: leading zeros and long numbers can change; use the spec
when that matters).

## Convert

```sh
W="$TMPDIR/job1"; mkdir -p "$W"
soffice --headless --convert-to pdf --outdir "$W" "/abs/path/book.xlsx"   # every sheet -> PDF
soffice --headless --convert-to xlsx --outdir "$W" "/abs/path/book.xls"   # old .xls -> new .xlsx copy
```

## Check

1. The script said "checks passed" (for a new file: `python3 "$S/scripts/ooxml.py" validate "$W/out.xlsx"`).
2. Real results, no errors: `S=<skill directory>; W="$TMPDIR/job1"; python3 "$S/scripts/xlsx_check.py" "$W/out.xlsx"`.
   It recalculates a scratch copy and lists every formula with its fresh
   result, then the errors (`#REF!`, `#DIV/0!`, `#NAME?`, `#VALUE!`, `#N/A`,
   `Err:5xx`). Fix every error you caused; check the totals the user cares
   about. Errors that were already there: mention them, do not fix unasked.
3. Only the intended cells changed:
   `python3 "$S/scripts/xlsx_dump.py" "$W/out.xlsx" > "$W/after.txt"; diff "$W/before.txt" "$W/after.txt"`
   (make `before.txt` from the original first, as in "Edit")
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
