"""pptx_outline.py FILE.pptx [--layouts]

Slides in show order: part, layout, shape names, text, speaker notes. Date,
footer and slide-number placeholders are marked ("date placeholder") and
fields show as {datetime1: 11/3/2026}: text in a datetime field is a cached
value that PowerPoint refreshes when it opens the file. --layouts also lists
the layouts and masters, but only their date/footer/slide-number placeholders
and fields. A logo or other picture is not text: use pptx_images.py list.
"""
import re
import sys
import zipfile
from html import unescape

import ooxml


def rels_of(z, part):
    d, f = part.rsplit('/', 1)
    try:
        xml = z.read(f'{d}/_rels/{f}.rels').decode('utf-8')
    except KeyError:
        return {}
    out = {}
    for r in re.findall(r'<Relationship [^>]*>', xml):
        t = re.search(r'Target="([^"]+)"', r).group(1)
        path = t.lstrip('/') if t.startswith('/') else d + '/' + t
        while '/../' in path:
            path = re.sub(r'[^/]+/\.\./', '', path, count=1)
        out[re.search(r'Id="([^"]+)"', r).group(1)] = (path, re.search(r'Type="[^"]*/([^"/]+)"', r).group(1))
    return out


PLACEHOLDER = {'dt': 'date placeholder', 'ftr': 'footer placeholder', 'sldNum': 'slide number placeholder'}
TEXT_OR_FIELD = re.compile(r'<a:fld\b([^>]*)>(.*?)</a:fld>|<a:t(?:\s[^>]*)?>([^<]*)</a:t>', re.S)


def paras(xml):
    ps = []
    for p in re.findall(r'<a:p>.*?</a:p>', xml, re.S):
        out = ''
        for m in TEXT_OR_FIELD.finditer(p):
            if m.group(3) is not None:
                out += unescape(m.group(3))
            else:
                kind = re.search(r'\btype="([^"]*)"', m.group(1))
                inner = ''.join(unescape(t) for t in re.findall(r'<a:t(?:\s[^>]*)?>([^<]*)</a:t>', m.group(2)))
                out += '{' + (kind.group(1) if kind else 'field') + ': ' + inner + '}'
        ps.append(out)
    return [p for p in ps if p]


def shape_lines(xml, special_only=False):
    lines = []
    for kind, block in re.findall(r'<p:(sp|graphicFrame)>(.*?)</p:\1>', xml, re.S):
        name = re.search(r'<p:cNvPr [^>]*name="([^"]*)"', block)
        ph = re.search(r'<p:ph\b[^>]*?\btype="([^"]*)"', block)
        what = PLACEHOLDER.get(ph.group(1)) if ph else None
        if special_only and not what and '<a:fld' not in block:
            continue
        text = paras(block)
        if text:
            label = unescape(name.group(1)) if name else kind
            lines.append(f'  [{label}{f" ({what})" if what else ""}] ' + ' / '.join(text))
    return lines


def slides_in_show_order(z):
    pres = z.read('ppt/presentation.xml').decode('utf-8')
    prels = rels_of(z, 'ppt/presentation.xml')
    return [(n, prels[rid][0], sid, rid)
            for n, (sid, rid) in enumerate(re.findall(r'<p:sldId [^>]*?id="(\d+)"[^>]*?r:id="([^"]+)"', pres), 1)]


def main():
    args = [a for a in sys.argv[1:] if a != '--layouts']
    if len(args) != 1:
        sys.exit(__doc__)
    ooxml.need_zip(args[0], 'FILE')
    z = zipfile.ZipFile(args[0])
    for n, part, sid, rid in slides_in_show_order(z):
        xml = z.read(part).decode('utf-8')
        hidden = ' HIDDEN' if re.search(r'<p:sld [^>]*show="0"', xml) else ''
        srels = rels_of(z, part)
        layout = next((p for p, t in srels.values() if t == 'slideLayout'), '?')
        print(f'== slide {n}: {part} (id {sid}, {rid}, layout {layout.rsplit("/", 1)[-1]}){hidden}')
        for line in shape_lines(xml):
            print(line)
        for p, t in srels.values():
            if t == 'notesSlide':
                body = [b for k, b in re.findall(r'<p:(sp)>(.*?)</p:\1>', z.read(p).decode('utf-8'), re.S) if 'type="body"' in b]
                note = ' / '.join(x for b in body for x in paras(b))
                if note:
                    print(f'  notes: {note}')
    if '--layouts' in sys.argv:
        num = lambda n: int(re.search(r'(\d+)\.xml$', n).group(1))
        for pat in (r'ppt/slideLayouts/slideLayout\d+\.xml', r'ppt/slideMasters/slideMaster\d+\.xml'):
            for part in sorted((n for n in z.namelist() if re.fullmatch(pat, n)), key=num):
                xml = z.read(part).decode('utf-8')
                title = re.search(r'<p:cSld\b[^>]*name="([^"]*)"', xml)
                lines = shape_lines(xml, True)
                if lines:
                    print(f'== {part}' + (f' "{unescape(title.group(1))}"' if title else ''))
                    for line in lines:
                        print(line)


if __name__ == '__main__':
    ooxml.cli(main)
