"""xlsx_set.py IN.xlsx OUT.xlsx SHEET CELL VALUE [CELL VALUE ...] [--text]

Set cells without writing XML. VALUE is a number (1250.5), TRUE/FALSE, a
formula (starts with "=", English function names, "," between arguments),
or text; "" empties the cell. --text keeps every VALUE as text (codes like
0012; a value with a leading zero is text anyway). "@file" reads VALUE from a file.

The cell keeps its format (s=). A new cell takes the format of the nearest
cell above it in the same column; missing rows and cells are added in order;
the sheet's dimension and the workbook's recalculate-on-open flag are updated.
Only the sheet part and workbook.xml change (plus calcChain.xml, which is
removed when a formula becomes a plain value). OUT is written by the same
checked pack as `ooxml.py pack`. Then run xlsx_check.py OUT for the real results.
"""
import re
import sys
import zipfile

import ooxml
import xlsx_dump

CELL = r'<c\b[^>]*?(?:/>|(?<!/)>.*?</c>)'
NUMBER = re.compile(r'[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?')


def column_number(letters):
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def column_letters(n):
    s = ''
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def split_ref(ref):
    m = re.fullmatch(r'([A-Za-z]{1,3})([1-9]\d*)', ref)
    if not m:
        sys.exit(f'ERROR: {ref!r} is not a cell reference like B5.')
    return m.group(1).upper(), int(m.group(2))


def cell_xml(ref, style, value, as_text):
    s = f' s="{style}"' if style else ''
    if value == '':
        return f'<c r="{ref}"{s}/>'
    if value.startswith('='):
        return f'<c r="{ref}"{s}><f>{ooxml.escape(value[1:])}</f></c>'
    if value.upper() in ('TRUE', 'FALSE') and not as_text:
        return f'<c r="{ref}"{s} t="b"><v>{int(value.upper() == "TRUE")}</v></c>'
    if not as_text and NUMBER.fullmatch(value) and not re.match(r'[+-]?0\d', value):
        return f'<c r="{ref}"{s}><v>{value.lstrip("+")}</v></c>'
    return f'<c r="{ref}"{s} t="inlineStr"><is><t xml:space="preserve">{ooxml.escape(value)}</t></is></c>'


def find_row(xml, number):
    for m in re.finditer(r'<row\b[^>]*?(?:/>|(?<!/)>.*?</row>)', xml, re.S):
        r = re.search(r'\sr="(\d+)"', m.group(0).split('>')[0])
        if r and int(r.group(1)) == number:
            return m
    return None


def style_above(xml, letters, number):
    best = None
    for m in re.finditer(rf'<c r="{letters}(\d+)"([^>]*)', xml):
        row = int(m.group(1))
        if row < number and (best is None or row > best[0]):
            style = re.search(r'\ss="(\d+)"', m.group(2))
            best = (row, style.group(1) if style else None)
    return best[1] if best else None


def set_cell(xml, ref, value, as_text):
    letters, number = split_ref(ref)
    ref = f'{letters}{number}'
    row = find_row(xml, number)
    old = None
    if row is not None:
        for m in re.finditer(CELL, row.group(0), re.S):
            if re.match(rf'<c r="{ref}"', m.group(0)):
                old = m
    if old is not None:
        text = old.group(0)
        if 't="shared"' in text or 't="array"' in text:
            sys.exit(f'ERROR: {ref} is part of a shared or array formula; change it by hand (references/cells.md).')
        style = re.search(r'\ss="(\d+)"', text.split('>')[0])
        new_cell = cell_xml(ref, style.group(1) if style else None, value, as_text)
        before = '(shared text)' if 't="s"' in text.split('>')[0] else re.sub(r'<[^>]+>', ' ', text).strip() or '(empty)'
        row_xml = row.group(0)[:old.start()] + new_cell + row.group(0)[old.end():]
        return xml[:row.start()] + row_xml + xml[row.end():], ('<f' in text and not value.startswith('=')), before
    new_cell = cell_xml(ref, style_above(xml, letters, number), value, as_text)
    if row is not None:
        text = row.group(0)
        head = re.match(r'<row\b[^>]*?>', text).group(0)
        if head.endswith('/>'):
            row_xml = head[:-2].rstrip() + '>' + new_cell + '</row>'
            row_xml = re.sub(r'\sspans="[^"]*"', '', row_xml)
        else:
            inner = text[len(head):-len('</row>')]
            at = len(inner)
            for m in re.finditer(CELL, inner, re.S):
                col = re.match(r'<c r="([A-Z]+)', m.group(0))
                if col and column_number(col.group(1)) > column_number(letters):
                    at = m.start()
                    break
            row_xml = re.sub(r'\sspans="[^"]*"', '', head) + inner[:at] + new_cell + inner[at:] + '</row>'
        return xml[:row.start()] + row_xml + xml[row.end():], False, '(empty)'
    new_row = f'<row r="{number}">{new_cell}</row>'
    if re.search(r'<sheetData\s*/>', xml):
        return re.sub(r'<sheetData\s*/>', f'<sheetData>{new_row}</sheetData>', xml, count=1), False, '(empty)'
    after = None
    for m in re.finditer(r'<row\b[^>]*?(?:/>|(?<!/)>.*?</row>)', xml, re.S):
        r = re.search(r'\sr="(\d+)"', m.group(0).split('>')[0])
        if r and int(r.group(1)) < number:
            after = m
    if after is not None:
        return xml[:after.end()] + new_row + xml[after.end():], False, '(empty)'
    return xml.replace('<sheetData>', '<sheetData>' + new_row, 1), False, '(empty)'


def grow_dimension(xml, refs):
    m = re.search(r'<dimension ref="([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?"/>', xml)
    if not m:
        return xml
    c1, r1, c2, r2 = m.group(1), int(m.group(2)), m.group(3) or m.group(1), int(m.group(4) or m.group(2))
    lo_c, hi_c, lo_r, hi_r = column_number(c1), column_number(c2), r1, r2
    for ref in refs:
        letters, number = split_ref(ref)
        lo_c, hi_c = min(lo_c, column_number(letters)), max(hi_c, column_number(letters))
        lo_r, hi_r = min(lo_r, number), max(hi_r, number)
    new = f'<dimension ref="{column_letters(lo_c)}{lo_r}:{column_letters(hi_c)}{hi_r}"/>'
    return xml[:m.start()] + new + xml[m.end():]


def recalc_on_open(workbook):
    m = re.search(r'<calcPr\b[^>]*?/>', workbook)
    if m:
        if 'fullCalcOnLoad' in m.group(0):
            return workbook
        return workbook[:m.start()] + m.group(0)[:-2].rstrip() + ' fullCalcOnLoad="1"/>' + workbook[m.end():]
    for closing in ('</definedNames>', '</sheets>'):
        if closing in workbook:
            return workbook.replace(closing, closing + '<calcPr fullCalcOnLoad="1"/>', 1)
    sys.exit('ERROR: workbook.xml has no <sheets>; is this a real workbook?')


def main():
    args = sys.argv[1:]
    as_text = '--text' in args
    args = [a for a in args if a != '--text']
    if len(args) < 5 or len(args) % 2 == 0:
        sys.exit(__doc__)
    src, out, sheet, pairs = args[0], args[1], args[2], args[3:]
    ooxml.need_zip(src, 'IN')
    ooxml.need_distinct(src, out)
    with zipfile.ZipFile(src) as z:
        sheets = xlsx_dump.sheets_of(z)
        has_chain = 'xl/calcChain.xml' in z.namelist()
    part = next((p for n, p, _ in sheets if n == sheet), None)
    if part is None:
        sys.exit(f'ERROR: no sheet named "{sheet}". Sheets: ' + ', '.join(f'"{n}"' for n, _, _ in sheets))
    xml = ooxml.read_part(src, part)
    lost_formula, refs = False, []
    for ref, value in zip(pairs[0::2], pairs[1::2]):
        value = ooxml.arg(value)
        xml, lost, before = set_cell(xml, ref, value, as_text)
        lost_formula = lost_formula or lost
        refs.append(ref.upper())
        print(f'{sheet}!{ref.upper()}: {before} -> {value or "(empty)"}')
    xml = grow_dimension(xml, refs)
    changes = {part: xml.encode('utf-8'), 'xl/workbook.xml': recalc_on_open(ooxml.read_part(src, 'xl/workbook.xml')).encode('utf-8')}
    if lost_formula and has_chain:
        rels = re.sub(r'<Relationship\b[^>]*Target="(?:/xl/)?calcChain\.xml"[^>]*/>', '', ooxml.read_part(src, 'xl/_rels/workbook.xml.rels'))
        types = re.sub(r'<Override\b[^>]*PartName="/xl/calcChain\.xml"[^>]*/>', '', ooxml.read_part(src, '[Content_Types].xml'))
        changes.update({'xl/_rels/workbook.xml.rels': rels.encode('utf-8'), '[Content_Types].xml': types.encode('utf-8'),
                        'xl/calcChain.xml': None})
    ooxml.repack(src, out, changes)
    print(f'next: python3 xlsx_check.py "{out}" for the recalculated results')


if __name__ == '__main__':
    ooxml.cli(main)
