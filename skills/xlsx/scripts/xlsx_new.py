"""xlsx_new.py SPEC.json OUT.xlsx -- build a new workbook. Standard library only.
SPEC: {"sheets": [{"name": "Sales", "rows": [["Item", "Qty"], ["Pens", 10]],
        "header": true, "widths": [24, 10], "formats": {"B": "#,##0.00"}, "freeze": "A2"}]}
A string starting with "=" is a formula. Numbers stay numbers; put codes like "0012" in quotes."""
import json, re, sys, zipfile
from xml.sax.saxutils import escape

spec = json.load(open(sys.argv[1], encoding='utf-8'))
fmts, xfs = [], [(0, 0)]          # xf = (numFmtId, bold)
def xf(numfmt, bold):
    nid = 0
    if numfmt:
        if numfmt not in fmts: fmts.append(numfmt)
        nid = 164 + fmts.index(numfmt)
    key = (nid, 1 if bold else 0)
    if key not in xfs: xfs.append(key)
    return xfs.index(key)
def col(n):
    s = ''
    while n: n, r = divmod(n - 1, 26); s = chr(65 + r) + s
    return s

sheets = []
for sh in spec['sheets']:
    rows, out = sh['rows'], []
    for ri, row in enumerate(rows, 1):
        cells = []
        for ci, v in enumerate(row, 1):
            if v is None or v == '': continue
            ref, bold = f'{col(ci)}{ri}', sh.get('header') and ri == 1
            s = xf(None if bold else sh.get('formats', {}).get(col(ci)), bold)
            st = f' s="{s}"' if s else ''
            if isinstance(v, bool):
                cells.append(f'<c r="{ref}"{st} t="b"><v>{int(v)}</v></c>')
            elif isinstance(v, (int, float)):
                cells.append(f'<c r="{ref}"{st}><v>{v}</v></c>')
            elif str(v).startswith('='):
                cells.append(f'<c r="{ref}"{st}><f>{escape(str(v)[1:])}</f></c>')
            else:
                cells.append(f'<c r="{ref}"{st} t="inlineStr"><is><t xml:space="preserve">{escape(str(v))}</t></is></c>')
        out.append(f'<row r="{ri}">{"".join(cells)}</row>')
    view = ''
    if sh.get('freeze'):
        m = re.match(r'([A-Z]+)(\d+)', sh['freeze']); c = sum((ord(ch) - 64) * 26 ** i for i, ch in enumerate(reversed(m.group(1)))) - 1; r = int(m.group(2)) - 1
        attrs = (f' xSplit="{c}"' if c else '') + (f' ySplit="{r}"' if r else '')
        view = f'<sheetViews><sheetView workbookViewId="0"><pane{attrs} topLeftCell="{sh["freeze"]}" activePane="bottomRight" state="frozen"/></sheetView></sheetViews>'
    cols = ''.join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i, w in enumerate(sh.get('widths', []), 1))
    sheets.append((sh['name'], f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">{view}' + (f'<cols>{cols}</cols>' if cols else '') + f'<sheetData>{"".join(out)}</sheetData></worksheet>'))

M = 'http://schemas.openxmlformats.org/'
z = zipfile.ZipFile(sys.argv[2], 'w', zipfile.ZIP_DEFLATED)
z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="' + M + 'package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' + ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, len(sheets) + 1)) + '</Types>')
z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="' + M + 'package/2006/relationships"><Relationship Id="rId1" Type="' + M + 'officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
z.writestr('xl/workbook.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<workbook xmlns="' + M + 'spreadsheetml/2006/main" xmlns:r="' + M + 'officeDocument/2006/relationships"><sheets>' + ''.join(f'<sheet name="{escape(n, {chr(34): "&quot;"})}" sheetId="{i}" r:id="rId{i}"/>' for i, (n, _) in enumerate(sheets, 1)) + '</sheets><calcPr fullCalcOnLoad="1"/></workbook>')
z.writestr('xl/_rels/workbook.xml.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="' + M + 'package/2006/relationships">' + ''.join(f'<Relationship Id="rId{i}" Type="' + M + f'officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(sheets) + 1)) + f'<Relationship Id="rId{len(sheets) + 1}" Type="' + M + 'officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
numfmts = ''.join(f'<numFmt numFmtId="{164 + i}" formatCode="{escape(f, {chr(34): "&quot;"})}"/>' for i, f in enumerate(fmts))
z.writestr('xl/styles.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<styleSheet xmlns="' + M + 'spreadsheetml/2006/main">' + (f'<numFmts count="{len(fmts)}">{numfmts}</numFmts>' if fmts else '') + '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>' + f'<cellXfs count="{len(xfs)}">' + ''.join(f'<xf numFmtId="{n}" fontId="{b}" fillId="0" borderId="0" xfId="0"' + (' applyNumberFormat="1"' if n else '') + (' applyFont="1"' if b else '') + '/>' for n, b in xfs) + '</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
for i, (_, xml) in enumerate(sheets, 1):
    z.writestr(f'xl/worksheets/sheet{i}.xml', xml)
z.close()
print('wrote', sys.argv[2], '|', ', '.join(f'{n}: {len(s["rows"])} rows' for (n, _), s in zip(sheets, spec['sheets'])))
