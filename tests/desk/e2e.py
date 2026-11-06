"""Acceptance test: the office skills, run the way NodeNova Desk's agent runs them.

Runs inside the desk image (tests/desk/run.sh starts it). It talks to the
image's tool server, the same Rust tools the agent calls: `skill_list`,
`skill_read`, `read`, `shell` (as the sandboxed user, offline) and `save`.
Every step follows a SKILL.md or one of its references; each check looks at
the result (text, values, pages, parts changed), not only at exit codes.
"""
import json
import re
import socket
import sys

SOCK = '/run/nn/tools.sock'
SESSION = 'skills-e2e'
results = []


def request(body):
    s = socket.socket(socket.AF_UNIX)
    s.connect(SOCK)
    s.sendall((json.dumps(body) + '\n').encode())
    buf = b''
    while not buf.endswith(b'\n'):
        chunk = s.recv(1 << 16)
        if not chunk:
            break
        buf += chunk
    return json.loads(buf)


def tool(tool_name, /, **args):
    r = request({'op': 'execute', 'session': SESSION, 'name': tool_name, 'args': args, 'callId': 'c'})
    if not r.get('ok'):
        return 'TOOL ERROR: ' + r.get('error', '?')
    return r['result']['content']


def sh(cmd, timeout=240):
    out = tool('shell', command=cmd, timeout=timeout)
    m = re.search(r'\[exit (\d+)\]\s*$', out)
    return out, (int(m.group(1)) if m else -1)


def check(name, ok, detail=''):
    results.append((name, bool(ok)))
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else '\n    ' + detail.strip().replace('\n', '\n    ')[-1500:]))


def scratch(path):
    return TMP + '/' + path


TMP = sh('echo "$TMPDIR"')[0].splitlines()[0].strip()

# ---------------------------------------------------------------- the skills
listed = tool('skill_list')
check('skill_list offers docx, xlsx, pptx, pdf', all(re.search(rf'^{n} — ', listed, re.M) for n in ['docx', 'xlsx', 'pptx', 'pdf']), listed)
for name in ['docx', 'xlsx', 'pptx']:
    body = tool('skill_read', name=name)
    check(f'skill_read {name} names its folder', f'[Skill directory: /opt/nodenova/skills/{name}]' in body, body[-300:])
ref = tool('read', path='/opt/nodenova/skills/docx/references/tracked-changes-and-comments.md', limit=1)
check('read opens a skill reference', ref.startswith('# Tracked changes and comments'), ref)
out = tool('write', path='/opt/nodenova/skills/docx/SKILL.md', content='x')
check('skills folder cannot be written', 'refused' in out, out)
out, code = sh('python3 -c "import lxml, defusedxml" && test -f /opt/nodenova/ooxml-schemas/transitional/wml.xsd && python3 --version && echo ready')
check('lxml, defusedxml and the ECMA-376 schemas are present', 'ready' in out, out)

# ------------------------------------------------------------------ docx
D = 'S=/opt/nodenova/skills/docx; W="$TMPDIR/docx"; mkdir -p "$W"; '
out, code = sh(D + r'''printf '# Terms\n\nPayment is due **within 30 days** of the invoice.\n\nLate payment incurs a fee.\n' > "$W/src.md"
pandoc "$W/src.md" -o "$W/p.docx" && soffice --headless --convert-to docx --outdir "$W/lo" "$W/p.docx" >/dev/null 2>&1 && ls "$W/lo/p.docx"''')
check('docx fixture written by LibreOffice (a client-style file)', code == 0, out)
out = tool('save', **{'from': scratch('docx/lo/p.docx'), 'path': '/work/contract.docx'})
check('save puts a new docx in the folder, Office check passed', re.match(r'Saved (/work/)?contract\.docx ', out) and 'Office check passed' in out, out)

out, code = sh(D + '''python3 "$S/scripts/ooxml.py" unpack /work/contract.docx "$W/x" && pandoc -t plain --track-changes=all /work/contract.docx > "$W/before.txt" && python3 "$S/scripts/docx_find.py" /work/contract.docx "within 30"''')
check('docx_find shows the paragraph and its runs', code == 0 and 'runs:' in out and 'within 30 days' in out, out)

# Edit 1: plain replacement inside one run.
out, code = sh(D + '''python3 "$S/scripts/ooxml.py" replace "$W/x/word/document.xml" '>within 30 days<' '>within 14 days<' ''')
check('ooxml.py replace changes exactly one occurrence', code == 0 and 'replaced 1' in out, out)

# Edit 2: a tracked change and a comment on "Late payment", as the reference says.
out, code = sh(D + r'''python3 - "$W/x/word/document.xml" <<'EOF'
import re, sys
p = sys.argv[1]; s = open(p, encoding='utf-8').read()
m = re.search(r'<w:r>(?:(?!</w:r>).)*?Late payment incurs a fee\.</w:t></w:r>', s, re.S)
run = m.group(0)
rpr = (re.search(r'<w:rPr>.*?</w:rPr>', run, re.S) or [''])[0] if '<w:rPr>' in run else ''
date = 'w:author="NodeNova Desk" w:date="2026-01-31T00:00:00Z"'
new = (f'<w:commentRangeStart w:id="903"/><w:del w:id="901" {date}><w:r>{rpr}<w:delText xml:space="preserve">Late payment incurs a fee.</w:delText></w:r></w:del>'
       f'<w:ins w:id="902" {date}><w:r>{rpr}<w:t xml:space="preserve">Late payment incurs a 2% fee.</w:t></w:r></w:ins>'
       f'<w:commentRangeEnd w:id="903"/><w:r><w:commentReference w:id="903"/></w:r>')
open(p, 'w', encoding='utf-8').write(s.replace(run, new, 1))
EOF
test -f "$W/x/word/comments.xml" && echo HAS_COMMENTS || echo NO_COMMENTS''')
check('tracked change written', code == 0, out)
if 'NO_COMMENTS' in out:
    out, code = sh(D + r'''cat > "$W/x/word/comments.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:comment w:id="903" w:author="NodeNova Desk" w:date="2026-01-31T00:00:00Z" w:initials="ND"><w:p><w:r><w:t>Agreed with finance.</w:t></w:r></w:p></w:comment></w:comments>
EOF
python3 "$S/scripts/ooxml.py" replace "$W/x/word/_rels/document.xml.rels" '</Relationships>' \
  '<Relationship Id="rIdNN903" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="comments.xml"/></Relationships>' &&
python3 "$S/scripts/ooxml.py" replace "$W/x/[Content_Types].xml" '</Types>' \
  '<Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/></Types>' ''')
    check('comments.xml created and registered (reference steps)', code == 0, out)

out, code = sh(D + 'python3 "$S/scripts/ooxml.py" pack /work/contract.docx "$W/x" "$W/out.docx"')
check('pack passes the schema and wiring checks', code == 0 and 'checks passed' in out and 'note:' not in out, out)
check('pack changed only the intended parts', all(p in out for p in ['word/document.xml', 'word/comments.xml']) and 'styles.xml' not in out, out)
out, code = sh(D + 'pandoc -t markdown --track-changes=all "$W/out.docx"')
check('pandoc sees the edit, the redline and the comment', 'within 14 days' in out and '.insertion' in out and '.deletion' in out and 'Agreed with finance' in out, out)
out, code = sh(D + 'soffice --headless --convert-to pdf --outdir "$W" "$W/out.docx" >/dev/null 2>&1 && pdftotext "$W/out.pdf" - && pdftoppm -png -r 60 -f 1 -l 1 "$W/out.pdf" "$W/page" && ls "$W"/page-1.png')
check('the edited docx opens and renders', code == 0 and 'within 14 days' in out, out)

# A broken edit is stopped by the skill's pack ...
out, code = sh(D + '''cp -r "$W/x" "$W/bad" && python3 "$S/scripts/ooxml.py" replace "$W/bad/word/document.xml" '<w:body>' '<w:body><w:bogus/>' && python3 "$S/scripts/ooxml.py" pack /work/contract.docx "$W/bad" "$W/bad.docx"; test -e "$W/bad.docx" && echo WRITTEN || echo NOT_WRITTEN''')
check('pack refuses a schema-invalid edit and writes nothing', 'NOT_WRITTEN' in out and "Element 'bogus'" in out, out)
# ... and a damaged package that skipped pack is stopped by Desk's own save.
out, code = sh(D + r'''python3 - "$W/out.docx" "$W/broken.docx" <<'EOF'
import sys, zipfile
src, dst = sys.argv[1:]
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zout:
    for n in zin.namelist():
        if n != 'word/comments.xml':
            zout.writestr(n, zin.read(n))
EOF
sha256sum /work/contract.docx''')
before_sha = out.split()[0]
out = tool('save', **{'from': scratch('docx/broken.docx'), 'path': '/work/contract.docx'})
after_sha = sh('sha256sum /work/contract.docx')[0].split()[0]
check("save refuses a damaged docx (Rust check) and leaves the user's file", out.startswith('ERROR') and 'points to missing part word/comments.xml' in out and before_sha == after_sha, out)

out = tool('save', **{'from': scratch('docx/out.docx'), 'path': '/work/contract.docx'})
check('save replaces the docx, listing the changed parts', re.match(r'Replaced (/work/)?contract\.docx ', out) and 'word/document.xml' in out and 'word/comments.xml' in out, out)
out, code = sh(D + '''cp -r "$W/x" "$W/acc" && python3 "$S/scripts/docx_accept.py" "$W/acc/word/document.xml" && python3 "$S/scripts/ooxml.py" pack /work/contract.docx "$W/acc" "$W/accepted.docx" && pandoc -t plain "$W/accepted.docx"''')
check('accepting all changes leaves the new text only', code == 0 and 'left: 0' in out and '2% fee' in out and 'incurs a fee.' not in out, out)
out, code = sh(D + r'''printf -- '---\ntitle: Memo\n---\n\n# Plan\n\n| A | B |\n|---|---:|\n| x | 1 |\n' > "$W/memo.md" && pandoc "$W/memo.md" -o "$W/memo.docx" && python3 "$S/scripts/ooxml.py" validate "$W/memo.docx"; echo done''')
check('a new docx from Markdown builds (pandoc)', 'done' in out and 'not a valid' not in out, out)

# ------------------------------------------------------------------ xlsx
X = 'S=/opt/nodenova/skills/xlsx; W="$TMPDIR/xlsx"; mkdir -p "$W"; '
out, code = sh(X + r'''cat > "$W/spec.json" <<'EOF'
{"sheets": [{"name": "Budget", "header": true, "freeze": "A2", "widths": [20, 8, 10, 12],
  "formats": {"C": "#,##0.00", "D": "#,##0.00"},
  "rows": [["Item", "Qty", "Price", "Total"], ["Pens & ink", 10, 1.5, "=B2*C2"], ["Pads", 4, 3, "=B3*C3"],
           ["Total", null, null, "=SUM(D2:D3)"]]},
 {"name": "Notes", "rows": [["Code", "Check"], ["0012", "=IF(Budget!D4>20,\"big\",\"small\")"]]}]}
EOF
python3 "$S/scripts/xlsx_new.py" "$W/spec.json" "$W/new.xlsx" && python3 "$S/scripts/ooxml.py" validate "$W/new.xlsx" && python3 "$S/scripts/xlsx_check.py" "$W/new.xlsx"''')
check('new workbook builds, validates and calculates', code == 0 and 'checks passed' in out and '=SUM(D2:D3)\t-> 27' in out and '-> big' in out and '0 formula error' in out, out)
out, code = sh(X + 'soffice --headless --convert-to xlsx --outdir "$W/lo" "$W/new.xlsx" >/dev/null 2>&1 && ls "$W/lo/new.xlsx"')
out = tool('save', **{'from': scratch('xlsx/lo/new.xlsx'), 'path': '/work/budget.xlsx'})
check('save puts a client-style workbook (LibreOffice-written) in the folder', re.match(r'Saved (/work/)?budget\.xlsx ', out) and 'Office check passed' in out, out)
out, code = sh(X + '''python3 "$S/scripts/ooxml.py" unpack /work/budget.xlsx "$W/x" >/dev/null && python3 "$S/scripts/xlsx_dump.py" /work/budget.xlsx > "$W/before.txt" && python3 "$S/scripts/xlsx_dump.py" /work/budget.xlsx Budget B2 A3''')
check('xlsx_dump prints the exact cell XML', code == 0 and '<c r="B2"' in out and '<c r="A3"' in out, out)
cells = dict(re.findall(r'^(B2|A3): (<c .*</c>)$', out, re.M))
new_b2 = re.sub(r'<v>[^<]*</v>', '<v>20</v>', cells.get('B2', ''))
s_attr = (re.search(r' s="\d+"', cells.get('A3', '')) or [''])[0]
new_a3 = f'<c r="A3"{s_attr} t="inlineStr"><is><t>Notepads</t></is></c>'
open_q = lambda t: "'" + t.replace("'", "'\\''") + "'"
out, code = sh(X + f'''python3 "$S/scripts/ooxml.py" replace "$W/x/xl/worksheets/sheet1.xml" {open_q(cells.get('B2', 'MISSING'))} {open_q(new_b2)} &&
python3 "$S/scripts/ooxml.py" replace "$W/x/xl/worksheets/sheet1.xml" {open_q(cells.get('A3', 'MISSING'))} {open_q(new_a3)} &&
CP=$(grep -o '<calcPr[^>]*>' "$W/x/xl/workbook.xml") && python3 "$S/scripts/ooxml.py" replace "$W/x/xl/workbook.xml" "$CP" "${{CP%/>}} fullCalcOnLoad=\\"1\\"/>" &&
python3 "$S/scripts/ooxml.py" pack /work/budget.xlsx "$W/x" "$W/out.xlsx" && python3 "$S/scripts/xlsx_check.py" "$W/out.xlsx" &&
python3 "$S/scripts/xlsx_dump.py" "$W/out.xlsx" > "$W/after.txt"; diff "$W/before.txt" "$W/after.txt"''')
check('cell edits pack cleanly and recalculate (Total 42, Check big)', 'checks passed' in out and '=SUM(D2:D3)\t-> 42' in out and '0 formula error' in out, out)
check('only the edited cells changed', '> B2\t20' in out and '> A3\tNotepads' in out and '> C2' not in out, out)
out = tool('save', **{'from': scratch('xlsx/out.xlsx'), 'path': '/work/budget.xlsx'})
check('save replaces the workbook: sheet and workbook parts changed', re.match(r'Replaced (/work/)?budget\.xlsx ', out) and 'xl/worksheets/sheet1.xml' in out and 'xl/workbook.xml' in out, out)
out, code = sh(X + '''cp -r "$W/x" "$W/bad" && python3 "$S/scripts/ooxml.py" replace "$W/bad/xl/worksheets/sheet1.xml" '<sheetData>' '<sheetData><row r="99"><c r="A99"><f>1/0</f><v>1</v></c></row>' && python3 "$S/scripts/ooxml.py" pack /work/budget.xlsx "$W/bad" "$W/bad.xlsx" && python3 "$S/scripts/xlsx_check.py" "$W/bad.xlsx"''')
check('xlsx_check reports a formula error the edit caused', '#DIV/0!' in out and '1 formula error' in out, out)

# ------------------------------------------------------------------ pptx
P = 'S=/opt/nodenova/skills/pptx; W="$TMPDIR/pptx"; mkdir -p "$W"; '
out, code = sh(P + r'''printf -- '---\ntitle: Q3 Review\n---\n\n## Results\n\n- Revenue up 12%%\n- Costs flat\n\n::: notes\nMention the North region.\n:::\n\n## Next\n\n- Hire\n- Ship\n' > "$W/deck.md" && pandoc "$W/deck.md" --slide-level=2 -o "$W/deck.pptx" && python3 "$S/scripts/ooxml.py" validate "$W/deck.pptx"''')
check('a new deck from Markdown builds and validates', code == 0 and 'checks passed' in out, out)
tool('save', **{'from': scratch('pptx/deck.pptx'), 'path': '/work/deck.pptx'})
out, code = sh(P + 'python3 "$S/scripts/pptx_outline.py" /work/deck.pptx | tee "$W/before.txt"')
check('pptx_outline lists slides in order with notes', 'slide 2: ppt/slides/slide2.xml' in out and 'notes: Mention the North region.' in out, out)
out, code = sh(P + r'''python3 "$S/scripts/ooxml.py" unpack /work/deck.pptx "$W/x" >/dev/null && cd "$W/x" &&
python3 "$S/scripts/ooxml.py" replace ppt/slides/slide2.xml '<a:t>Costs flat</a:t>' '<a:t>Costs down 3%</a:t>' &&
cp ppt/slides/slide2.xml ppt/slides/slide9.xml &&
python3 -c "import re; s = open('ppt/slides/_rels/slide2.xml.rels').read(); open('ppt/slides/_rels/slide9.xml.rels', 'w').write(re.sub(r'<Relationship [^>]*notesSlide[^>]*/>', '', s))" &&
python3 "$S/scripts/ooxml.py" replace "[Content_Types].xml" '</Types>' '<Override PartName="/ppt/slides/slide9.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/></Types>' &&
python3 "$S/scripts/ooxml.py" replace ppt/_rels/presentation.xml.rels '</Relationships>' '<Relationship Id="rIdNN9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide9.xml"/></Relationships>' &&
python3 "$S/scripts/ooxml.py" replace ppt/presentation.xml '</p:sldIdLst>' '<p:sldId id="900" r:id="rIdNN9"/></p:sldIdLst>' &&
cd / && python3 "$S/scripts/ooxml.py" pack /work/deck.pptx "$W/x" "$W/out.pptx" && python3 "$S/scripts/pptx_outline.py" "$W/out.pptx" > "$W/after.txt"; diff "$W/before.txt" "$W/after.txt";
soffice --headless --convert-to pdf --outdir "$W" "$W/out.pptx" >/dev/null 2>&1 && pdfinfo "$W/out.pdf" | grep Pages''')
check('edit text and duplicate a slide: pack passes, 4 slides render', 'checks passed' in out and 'Costs down 3%' in out and 'slide9.xml (id 900' in out and re.search(r'Pages:\s+4', out), out)
out = tool('save', **{'from': scratch('pptx/out.pptx'), 'path': '/work/deck.pptx'})
check('save replaces the deck, listing the changed parts', re.match(r'Replaced (/work/)?deck\.pptx ', out) and 'ppt/slides/slide9.xml' in out, out)

# ------------------------------------------------------------------ pdf
F = 'W="$TMPDIR/pdf"; mkdir -p "$W"; '
out, code = sh(F + '''soffice --headless --convert-to pdf --outdir "$W" /work/contract.docx >/dev/null 2>&1 && soffice --headless --convert-to pdf --outdir "$W" /work/deck.pptx >/dev/null 2>&1 &&
qpdf --empty --pages "$W/contract.pdf" "$W/deck.pdf" -- "$W/merged.pdf" && qpdf "$W/merged.pdf" --pages . 2-3 -- "$W/part.pdf" && qpdf "$W/part.pdf" --rotate=+90:1 "$W/rot.pdf" &&
pdfinfo "$W/merged.pdf" | grep Pages; pdfinfo "$W/rot.pdf" | grep Pages; pdftotext -layout "$W/merged.pdf" - | grep -c "within 14 days"''')
check('merge, extract and rotate pages (qpdf)', code == 0 and re.search(r'Pages:\s+5', out) and re.search(r'Pages:\s+2', out), out)
out, code = sh(F + r'''python3 - "$W/form.pdf" <<'EOF'
import sys
objs = ["<< /Type /Catalog /Pages 2 0 R /AcroForm << /Fields [4 0 R] /NeedAppearances true >> >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Annots [4 0 R] >>",
        "<< /Type /Annot /Subtype /Widget /FT /Tx /T (FullName) /Rect [100 700 300 720] /P 3 0 R /DA (/Helv 12 Tf 0 g) >>"]
out = b"%PDF-1.4\n"; offs = []
for i, o in enumerate(objs, 1):
    offs.append(len(out)); out += f"{i} 0 obj\n{o}\nendobj\n".encode()
x = len(out); out += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode() + b"".join(f"{o:010d} 00000 n \n".encode() for o in offs)
out += f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n".encode()
open(sys.argv[1], "wb").write(out)
EOF
pdftk "$W/form.pdf" dump_data_fields_utf8 | grep FieldName
cat > "$W/values.xfdf" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<xfdf xmlns="http://ns.adobe.com/xfdf/"><fields><field name="FullName"><value>Zoë &amp; Co</value></field></fields></xfdf>
EOF
pdftk "$W/form.pdf" fill_form "$W/values.xfdf" output "$W/filled.pdf" && pdftk "$W/filled.pdf" dump_data_fields_utf8 | grep FieldValue''')
check('fill a PDF form (pdftk, UTF-8 XFDF)', 'FieldValue: Zoë & Co' in out, out)
out, code = sh(F + '''mkdir -p "$W/ocr" && pdftoppm -png -r 300 -f 1 -l 1 "$W/merged.pdf" "$W/ocr/p" && for f in "$W"/ocr/p-*.png; do tesseract "$f" "${f%.png}" pdf 2>/dev/null; done && pdfunite "$W"/ocr/p-*.pdf "$W/searchable.pdf" && pdftotext "$W/searchable.pdf" - | tr -s ' \\n' ' ' ''', 300)
check('OCR a page into a searchable PDF (tesseract)', 'Payment' in out and 'days' in out, out)
out = tool('save', **{'from': scratch('pdf/merged.pdf'), 'path': '/work/Contract - full set.pdf'})
check('save puts a PDF in the folder (no Office check for PDF)', re.match(r'Saved (/work/)?Contract\ \-\ full\ set\.pdf ', out) and 'Office check' not in out, out)

# ------------------------------------------------------------------ summary
failed = [n for n, ok in results if not ok]
print(f'\n{len(results) - len(failed)}/{len(results)} checks passed')
sys.exit(1 if failed else 0)
