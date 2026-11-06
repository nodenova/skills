"""docx_find.py INPUT TEXT [PART] [--xml]

INPUT is a .docx, an unpacked folder, or one XML part file. PART defaults to
word/document.xml (use word/header1.xml etc. for other parts of a .docx or folder).
Prints every paragraph containing TEXT (any case): its number, text, runs with
their formatting, and the paragraph mark's formatting. --xml adds the exact XML.
Use the number with `docx_format.py --paragraph N`.
"""
import re
import sys

import ooxml


def props(xml_children):
    out = []
    for tag, xml in xml_children:
        if tag == 'w:rPrChange':
            continue
        name = tag.split(':')[-1]
        attr = 'w:ascii' if name == 'rFonts' else 'w:val'
        val = re.search(rf'{attr}="([^"]*)"', xml)
        out.append(name + ('=' + val.group(1) if val else ''))
    return ' '.join(out)


def rpr_children(body):
    kids = ooxml.top_children(body)
    if kids and kids[0][0] == 'w:rPr':
        inner = re.sub(r'^<w:rPr[^>]*?/?>|</w:rPr>$', '', kids[0][1])
        return ooxml.top_children(inner)
    return []


def describe_run(body):
    text = ''
    for tag, xml in ooxml.top_children(body):
        if tag == 'w:t':
            text += ooxml.unescape(re.sub(r'<[^>]*>', '', xml))
        elif tag == 'w:tab':
            text += '\t'
        elif tag == 'w:br':
            text += '\n'
    return f'{text!r} [{props(rpr_children(body))}]'


def describe_paragraph(par):
    body = re.sub(r'^<w:p(?=[\s>])[^>]*?>', '', par)
    kids = ooxml.top_children(body)
    style, mark = '', ''
    if kids and kids[0][0] == 'w:pPr':
        inner = re.sub(r'^<w:pPr[^>]*?>|</w:pPr>$', '', kids[0][1])
        for tag, xml in ooxml.top_children(inner):
            if tag == 'w:pStyle':
                style = re.search(r'w:val="([^"]*)"', xml).group(1)
            elif tag == 'w:rPr':
                mark = props(ooxml.top_children(re.sub(r'^<w:rPr[^>]*?>|</w:rPr>$', '', xml)))
    runs = [describe_run(m.group(1)) for m in re.finditer(r'<w:r(?=[\s>])[^>]*?(?<!/)>(.*?)</w:r>', par, re.S)]
    return style, mark, runs


def main():
    args = sys.argv[1:]
    show_xml = '--xml' in args
    args = [a for a in args if a != '--xml']
    if len(args) not in (2, 3) or not args[1]:
        sys.exit(__doc__)
    src, needle = args[0], args[1]
    part = args[2] if len(args) == 3 else 'word/document.xml'
    xml = ooxml.read_part(src, part)
    pars = ooxml.paragraph_matches(xml, ooxml.DOCX)
    texts = [ooxml.paragraph_text(m.group(0), ooxml.DOCX) for m in pars]
    hits = [n for n, t in enumerate(texts, 1) if needle.lower() in t.lower()]
    if not hits:
        sys.exit(ooxml.no_text_match_message(texts, needle, part))
    for n in hits:
        style, mark, runs = describe_paragraph(pars[n - 1].group(0))
        print(f'--- paragraph {n} ({part})')
        print('text:', texts[n - 1])
        print('runs:', ' | '.join(runs))
        print('style:', style or '-', '| mark:', f'[{mark}]')
        if show_xml:
            p = pars[n - 1].group(0)
            print(p if len(p) < 4000 else p[:4000] + ' ...[cut]')


if __name__ == '__main__':
    ooxml.cli(main)
