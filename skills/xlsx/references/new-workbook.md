# New workbook spec (`xlsx_new.py`)

```sh
cat > "$W/spec.json" <<'EOF'
{"sheets": [
  {"name": "Sales", "header": true, "freeze": "A2",
   "widths": [24, 10, 12, 14],
   "formats": {"C": "#,##0.00", "D": "#,##0.00"},
   "rows": [["Item", "Qty", "Price", "Total"],
            ["Pens", 10, 1.5, "=B2*C2"],
            ["Pads", 4, 3, "=B3*C3"],
            ["Total", null, null, "=SUM(D2:D3)"]]},
  {"name": "Notes", "rows": [["Code", "Comment"], ["0012", "codes stay text"]]}
]}
EOF
python3 "$S/scripts/xlsx_new.py" "$W/spec.json" "$W/out.xlsx"
python3 "$S/scripts/xlsx_check.py" "$W/out.xlsx"
```

| Key | Meaning |
|---|---|
| `name` | sheet tab name (at most 31 characters, none of `: \ / ? * [ ]`) |
| `rows` | list of rows, each a list of cells; `null` leaves a cell empty |
| `header` | `true` makes row 1 bold |
| `freeze` | `"A2"` keeps row 1 visible when scrolling; `"B2"` also column A |
| `widths` | column widths in characters, from column A |
| `formats` | Excel number format per column letter |

Cells:

- A string starting with `=` is a formula (`"=SUM(B2:B9)"`, `"='Other sheet'!B4"`).
- A JSON number is a number; `true`/`false` are booleans.
- Any other string is text, exactly as written: `"0012"` keeps its zeros,
  `"2025-01-31"` stays text.

Number formats: `"#,##0"`, `"#,##0.00"`, `"0%"`, `"0.0%"`, `"yyyy-mm-dd"`,
`"dd/mm/yyyy"`, `"[$€-x-euro2] #,##0.00"`, `"[$£-809]#,##0.00"`.

Dates that must calculate: write the Excel day number (days since 1899-12-30;
2025-01-31 is 45688) and give the column a date format:
`python3 -c "import datetime as d; print((d.date(2025,1,31)-d.date(1899,12,30)).days)"`.

The file has no stored results; it recalculates when opened, and
`xlsx_check.py` shows the results.
