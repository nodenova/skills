"""xlsx_dump.py FILE.xlsx [SHEET [CELL ...]]
No SHEET: every cell of every sheet (value, or =formula -> stored value).
SHEET and CELLs (B5 C7): the exact XML of those cells, to copy into `ooxml.py replace`.
To change cells without writing XML, use xlsx_set.py."""
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

import ooxml

try:
    from defusedxml.ElementTree import fromstring
except ImportError:
    fromstring = ET.fromstring
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
RID = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'


def sheets_of(z):
    rels = {r.get('Id'): r.get('Target') for r in fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    out = []
    for sh in fromstring(z.read('xl/workbook.xml')).find('m:sheets', NS):
        target = rels[sh.get(RID)]
        out.append((sh.get('name'), target.lstrip('/') if target.startswith('/') else 'xl/' + target, sh.get('state')))
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ooxml.need_zip(sys.argv[1], 'FILE')
    z = zipfile.ZipFile(sys.argv[1])
    want, refs = (sys.argv[2] if len(sys.argv) > 2 else None), sys.argv[3:]
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS):
            shared.append(''.join(t.text or '' for t in si.iter('{%s}t' % NS['m'])))
    found = False
    for name, part, state in sheets_of(z):
        if want and name != want:
            continue
        found = True
        hidden = f' ({state})' if state not in (None, 'visible') else ''
        print(f'== sheet "{name}" ({part}){hidden}')
        if refs:
            xml = z.read(part).decode('utf-8')
            for ref in refs:
                m = re.search(r'<c r="%s"(?:[^>]*/>|[^>]*>.*?</c>)' % ref, xml, re.S)
                if m:
                    print(f'{ref}: {m.group(0)}')
                    continue
                row = re.search(r'\d+', ref).group(0)
                r = re.search(r'<row r="%s"[^>]*?(?:/>|>.*?</row>)' % row, xml, re.S)
                print(f'{ref}: no cell. ' + (f'Row {row} XML: {r.group(0)[:2000]}' if r else f'No row {row} either.'))
            continue
        for c in fromstring(z.read(part)).iter('{%s}c' % NS['m']):
            f, v, t = c.find('m:f', NS), c.find('m:v', NS), c.get('t')
            val = v.text if v is not None else ''
            if t == 's' and val:
                val = shared[int(val)]
            elif t == 'inlineStr':
                val = ''.join(x.text or '' for x in c.iter('{%s}t' % NS['m']))
            if f is not None:
                print(f'{c.get("r")}\t={f.text or "(shared formula " + str(f.get("si")) + ")"}\t-> {val}')
            elif val != '':
                print(f'{c.get("r")}\t{val}')
    if want and not found:
        names = ', '.join(f'"{n}"' for n, _, _ in sheets_of(z))
        sys.exit(f'ERROR: no sheet named "{want}". Sheets: {names}')


if __name__ == '__main__':
    ooxml.cli(main)
