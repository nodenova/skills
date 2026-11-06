"""pptx_outline.py FILE.pptx -- slides in show order: part, shape names, text, notes."""
import re, sys, zipfile
z = zipfile.ZipFile(sys.argv[1])

def rels_of(part):
    d, f = part.rsplit('/', 1)
    try: xml = z.read(f'{d}/_rels/{f}.rels').decode('utf-8')
    except KeyError: return {}
    out = {}
    for r in re.findall(r'<Relationship [^>]*>', xml):
        t = re.search(r'Target="([^"]+)"', r).group(1)
        path = t.lstrip('/') if t.startswith('/') else d + '/' + t
        while '/../' in path: path = re.sub(r'[^/]+/\.\./', '', path, count=1)
        out[re.search(r'Id="([^"]+)"', r).group(1)] = (path, re.search(r'Type="[^"]*/([^"/]+)"', r).group(1))
    return out

def paras(xml):
    ps = [''.join(re.findall(r'<a:t>([^<]*)</a:t>', p)) for p in re.findall(r'<a:p>.*?</a:p>', xml, re.S)]
    return [p for p in ps if p]

pres = z.read('ppt/presentation.xml').decode('utf-8')
prels = rels_of('ppt/presentation.xml')
for n, (sid, rid) in enumerate(re.findall(r'<p:sldId [^>]*?id="(\d+)"[^>]*?r:id="([^"]+)"', pres), 1):
    part = prels[rid][0]
    xml = z.read(part).decode('utf-8')
    hidden = ' HIDDEN' if re.search(r'<p:sld [^>]*show="0"', xml) else ''
    srels = rels_of(part)
    layout = next((p for p, t in srels.values() if t == 'slideLayout'), '?')
    print(f'== slide {n}: {part} (id {sid}, {rid}, layout {layout.rsplit("/", 1)[-1]}){hidden}')
    for kind, block in re.findall(r'<p:(sp|graphicFrame)>(.*?)</p:\1>', xml, re.S):
        name = re.search(r'<p:cNvPr [^>]*name="([^"]*)"', block)
        text = paras(block)
        if text:
            print(f'  [{name.group(1) if name else kind}] ' + ' / '.join(text))
    for p, t in srels.values():
        if t == 'notesSlide':
            body = [b for k, b in re.findall(r'<p:(sp)>(.*?)</p:\1>', z.read(p).decode('utf-8'), re.S) if 'type="body"' in b]
            note = ' / '.join(x for b in body for x in paras(b))
            if note: print(f'  notes: {note}')
