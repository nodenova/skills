"""docx_header.py IN.docx OUT.docx --text TEXT [--footer] [--align left|center|right] [--replace] [--type default|first|even]

Put TEXT in the header (or, with --footer, the footer) of every page. A
section without a header gets a new one; an existing header keeps its
pictures, fields and other paragraphs and gets one more paragraph (an empty
paragraph is reused). The first-page header is filled when a section uses
"different first page", the even-page header when the document has
"different odd and even pages", and any header type already present is
filled too; --type limits it to one type. --replace swaps the existing text
paragraphs instead of adding one (pictures, page-number fields and tables
stay); a header that already has TEXT is left alone. "@file" reads TEXT from
a file. Written through the checked pack: other parts stay byte-identical.
"""
import re
import sys
import zipfile
from xml.sax.saxutils import escape

import ooxml

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = ooxml.R
KINDS = {
    'header': ('hdr', 'application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml', 'Header'),
    'footer': ('ftr', 'application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml', 'Footer'),
}
AFTER_JC = ('w:textDirection', 'w:textAlignment', 'w:textboxTightWrap', 'w:outlineLvl', 'w:divId', 'w:cnfStyle',
            'w:rPr', 'w:sectPr', 'w:pPrChange')
SPECIAL = re.compile(r'<w:(?:drawing|pict|fldChar|fldSimple|object)\b|<mc:AlternateContent')


def is_on(xml, tag):
    m = re.search(rf'<{tag}(?=[\s/>])[^>]*>', xml)
    return bool(m) and not re.search(r'w:val="(?:0|false|off)"', m.group(0))


def set_jc(ppr, align):
    if ppr is None:
        return f'<w:pPr><w:jc w:val="{align}"/></w:pPr>' if align else ''
    if not align:
        return ppr
    selfclosed = re.match(r'<w:pPr(?=[\s/>])[^>]*?/>$', ppr)
    opening = re.match(r'<w:pPr(?=[\s/>])[^>]*?(?<!/)>', ppr).group(0) if not selfclosed else ppr[:-2] + '>'
    inner = '' if selfclosed else ppr[len(opening):-len('</w:pPr>')]
    kids = [(t, x) for t, x in ooxml.top_children(inner) if t != 'w:jc']
    at = next((i for i, (t, _) in enumerate(kids) if t in AFTER_JC), len(kids))
    kids.insert(at, ('w:jc', f'<w:jc w:val="{align}"/>'))
    return opening + ''.join(x for _, x in kids) + '</w:pPr>'


def split_paragraph(p):
    m = re.match(r'(<w:p(?=[\s>/])[^>]*?)(/?)>', p)
    opening = m.group(1) + '>'
    inner = '' if m.group(2) else p[m.end():-len('</w:p>')]
    kids = ooxml.top_children(inner)
    ppr = kids[0][1] if kids and kids[0][0] == 'w:pPr' else None
    rest = inner[len(ppr):] if ppr else inner
    return opening, ppr, rest


def run_xml(text, rpr):
    return f'<w:r>{rpr or ""}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def first_rpr(p):
    m = re.search(r'<w:r(?=[\s>])[^>]*?(?<!/)>(<w:rPr(?:\s[^>]*)?>.*?</w:rPr>|<w:rPr\s*/>)?<w:t[\s>]', p, re.S)
    return m.group(1) if m else None


def has_text(p):
    return bool(re.search(r'<w:t(?:\s[^>]*)?>[^<]+</w:t>', p))


def is_empty(p):
    opening, ppr, rest = split_paragraph(p)
    return not re.search(r'<w:(?:r|hyperlink|fldSimple|smartTag|sdt|ins|del|bookmarkStart)\b|<mc:', rest)


def edit_story(xml, text, align, replace, style):
    """Add or replace TEXT in a header/footer part; returns (xml, what happened)."""
    xml = re.sub(r'<(w:(?:hdr|ftr))((?:\s[^>]*?)?)/>', r'<\1\2></\1>', xml, count=1)
    root = re.search(r'<w:(?:hdr|ftr)(?=[\s>])[^>]*>', xml)
    close = xml.rindex('</w:')
    kids = ooxml.top_children(xml[root.end():close])
    paras = [i for i, (t, x) in enumerate(kids) if t == 'w:p']
    if any(ooxml.paragraph_text(kids[i][1], ooxml.DOCX).strip() == text for i in paras):
        return xml, 'already has this text'
    texty = [i for i in paras if has_text(kids[i][1]) and not SPECIAL.search(kids[i][1])]
    if replace and texty:
        i0 = texty[0]
        opening, ppr, _ = split_paragraph(kids[i0][1])
        new_p = f'{opening}{set_jc(ppr, align)}{run_xml(text, first_rpr(kids[i0][1]))}</w:p>'
        kids[i0] = ('w:p', new_p)
        for i in reversed(texty[1:]):
            del kids[i]
        what = f'replaced {len(texty)} text paragraph(s)'
    else:
        empty = next((i for i in paras if is_empty(kids[i][1]) and not has_text(kids[i][1])), None)
        if empty is not None:
            opening, ppr, _ = split_paragraph(kids[empty][1])
            kids[empty] = ('w:p', f'{opening}{set_jc(ppr, align)}{run_xml(text, None)}</w:p>')
            what = 'filled the empty paragraph'
        else:
            ppr = set_jc(f'<w:pPr>{style}</w:pPr>' if style else None, align)
            kids.append(('w:p', f'<w:p>{ppr}{run_xml(text, None)}</w:p>'))
            what = 'added a paragraph'
    return xml[:root.end()] + ''.join(x for _, x in kids) + xml[close:], what


def new_story(kind, text, align, style):
    tag = KINDS[kind][0]
    ppr = set_jc(f'<w:pPr>{style}</w:pPr>' if style else None, align)
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n<w:{tag} xmlns:w="{W}" xmlns:r="{R}">'
            f'<w:p>{ppr}{run_xml(text, None)}</w:p></w:{tag}>')


def main():
    args = sys.argv[1:]
    opts = {'--align': None, '--type': None, '--text': None}
    flags = set()
    rest = []
    i = 0
    while i < len(args):
        if args[i] in opts and i + 1 < len(args):
            opts[args[i]] = args[i + 1]
            i += 2
        elif args[i] in ('--footer', '--replace'):
            flags.add(args[i])
            i += 1
        else:
            rest.append(args[i])
            i += 1
    if len(rest) != 2 or opts['--text'] is None or opts['--align'] not in (None, 'left', 'center', 'right') \
            or opts['--type'] not in (None, 'default', 'first', 'even'):
        sys.exit(__doc__)
    src, out = rest
    text = ooxml.arg(opts['--text'])
    if not text.strip() or '\n' in text:
        sys.exit('ERROR: --text must be one non-empty line.')
    align, only = opts['--align'], opts['--type']
    kind = 'footer' if '--footer' in flags else 'header'
    tag, ctype, style_id = KINDS[kind]
    ooxml.need_zip(src, 'IN')
    ooxml.need_distinct(src, out)
    with zipfile.ZipFile(src) as z:
        names = z.namelist()
        if 'word/document.xml' not in names:
            sys.exit('ERROR: IN has no word/document.xml; it is not a Word document.')
        doc = z.read('word/document.xml').decode('utf-8')
        rels = z.read('word/_rels/document.xml.rels').decode('utf-8') if 'word/_rels/document.xml.rels' in names else \
            f'<Relationships xmlns="{ooxml.PKG_RELS}"></Relationships>'
        types = z.read('[Content_Types].xml').decode('utf-8')
        settings = z.read('word/settings.xml').decode('utf-8') if 'word/settings.xml' in names else ''
        styles = z.read('word/styles.xml').decode('utf-8') if 'word/styles.xml' in names else ''
        story_xml = {n: z.read(n).decode('utf-8') for n in names if re.fullmatch(rf'word/(?:header|footer)\d*\.xml', n)}
    style = f'<w:pStyle w:val="{style_id}"/>' if re.search(rf'w:styleId="{style_id}"', styles) else ''
    odd_even = is_on(settings, 'w:evenAndOddHeaders')
    rel_of = {}
    for tagxml in re.findall(r'<Relationship\b[^>]*>', rels):
        rid = re.search(r'\bId="([^"]*)"', tagxml)
        tgt = re.search(r'\bTarget="([^"]*)"', tagxml)
        if rid and tgt:
            rel_of[rid.group(1)] = ooxml.resolve_target('word/_rels/document.xml.rels', tgt.group(1))

    masked = re.sub(r'<w:sectPrChange\b.*?</w:sectPrChange>', lambda m: ' ' * len(m.group(0)), doc, flags=re.S)
    sects = list(re.finditer(r'<w:sectPr(?=[\s>/])[^>]*?(?:/>|(?<!/)>.*?</w:sectPr>)', masked, re.S))
    if not sects:
        sys.exit('ERROR: the document has no <w:sectPr> section properties, so there is nowhere to attach a header.')
    used_ids = set(rel_of)
    next_id = max([int(x) for i in used_ids for x in re.findall(r'(\d+)$', i)] + [0]) + 1
    next_part = max([int(re.search(rf'(\d*)\.xml$', n).group(1) or 0) for n in story_xml if n.startswith(f'word/{kind}')] + [0]) + 1
    current, edit_parts, created, inserts, log, kinds_of = {}, [], {}, [], [], {}
    for s in sects:
        block = s.group(0)
        refs = {}
        for t in re.findall(rf'<w:{kind}Reference\b[^>]*>', block):
            refs[(re.search(r'w:type="([^"]*)"', t) or [0, 'default'])[1]] = re.search(r'r:id="([^"]*)"', t).group(1)
        if only:
            wanted = [only]
        else:
            wanted = ['default'] + (['first'] if is_on(block, 'w:titlePg') else []) + (['even'] if odd_even else [])
            wanted += [t for t in refs if t not in wanted]
        add = ''
        for t in wanted:
            if t in refs:
                part = rel_of.get(refs[t])
                if part not in story_xml:
                    sys.exit(f'ERROR: {kind} relationship {refs[t]} points to {part}, which is not in the file.')
                current[t] = part
            elif t not in current:
                part = f'word/{kind}{next_part}.xml'
                rid = f'rId{next_id}'
                next_part += 1
                next_id += 1
                created[part] = (rid, t)
                current[t] = part
                add += f'<w:{kind}Reference w:type="{t}" r:id="{rid}"/>'
            if current[t] not in edit_parts:
                edit_parts.append(current[t])
            if t not in kinds_of.setdefault(current[t], []):
                kinds_of[current[t]].append(t)
        if add:
            if block.endswith('/>') and not block.endswith('</w:sectPr>'):
                inserts.append((s.start(), s.end(), doc[s.start():s.end()][:-2] + '>' + add + '</w:sectPr>'))
            else:
                at = s.start() + re.match(r'<w:sectPr(?=[\s>/])[^>]*?>', block).end()
                inserts.append((at, at, add))
    changes = {}
    for part in edit_parts:
        if part in created:
            xml = new_story(kind, text, align, style)
            what = 'created'
        else:
            xml, what = edit_story(story_xml[part], text, align, '--replace' in flags, style)
        if part in created or xml != story_xml[part]:
            changes[part] = xml.encode('utf-8')
        log.append(f'{part} ({", ".join(kinds_of[part])}): {what}')
    if inserts:
        for a, b, repl in sorted(inserts, reverse=True):
            doc = doc[:a] + repl + doc[b:]
        if 'xmlns:r=' not in doc[:doc.index('>', doc.index('<w:document'))]:
            doc = doc.replace('<w:document', f'<w:document xmlns:r="{R}"', 1)
        changes['word/document.xml'] = doc.encode('utf-8')
        add_rels = ''.join(f'<Relationship Id="{rid}" Type="{R}/{kind}" Target="{p[len("word/"):]}"/>' for p, (rid, _) in created.items())
        rels = re.sub(r'<Relationships([^>]*?)/>', r'<Relationships\1></Relationships>', rels).replace('</Relationships>', add_rels + '</Relationships>')
        changes['word/_rels/document.xml.rels'] = rels.encode('utf-8')
        overrides = ''.join(f'<Override PartName="/{p}" ContentType="{ctype}"/>' for p in created)
        changes['[Content_Types].xml'] = types.replace('</Types>', overrides + '</Types>').encode('utf-8')
    if not changes:
        print(f'nothing to change: every {kind} already has this text')
        ooxml.repack(src, out, {})
        return
    print(f'{kind} text set in {len(sects)} section(s):')
    for line in log:
        print(' ', line)
    ooxml.repack(src, out, changes)


if __name__ == '__main__':
    ooxml.cli(main)
