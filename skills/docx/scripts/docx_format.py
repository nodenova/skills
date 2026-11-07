"""docx_format.py IN.docx OUT.docx PICK FORMAT... [--part PART]

Change character formatting of whole paragraphs without writing XML.

PICK (one):
  --paragraph N                 paragraph number as printed by docx_find.py; repeat it
                                or give a list (--paragraph 3,7,12) for several
  --paragraph-containing TEXT   paragraphs whose text contains TEXT (any case)
    --occurrence K              only the K-th such paragraph (1 = first)
    --all                       every such paragraph
FORMAT (one or more):
  --color FF0000|red|auto       replaces any colour, theme colour included
  --bold | --no-bold    --italic | --no-italic    --underline | --no-underline
  --size 14                     points
  --highlight yellow|none       --font NAME

Every run of the paragraph gets the format, and so does the paragraph mark's
own run properties when it has them. Properties are written in schema order,
only word/document.xml (or --part word/header1.xml, word/footer1.xml, ...)
changes, and OUT is written by the same checked pack as `ooxml.py pack`.
"""
import argparse
import re
import sys

import ooxml

ORDER = ('rStyle rFonts b bCs i iCs caps smallCaps strike dstrike outline shadow emboss imprint noProof '
         'snapToGrid vanish webHidden color spacing w kern position sz szCs highlight u effect bdr shd '
         'fitText vertAlign rtl cs em lang eastAsianLayout specVanish oMath').split()
RANK = {name: i for i, name in enumerate(ORDER)}
FOREIGN, LAST = 500, 1000
COLORS = {'black': '000000', 'white': 'FFFFFF', 'red': 'FF0000', 'green': '008000', 'blue': '0000FF',
          'yellow': 'FFFF00', 'orange': 'FFA500', 'purple': '800080', 'gray': '808080', 'grey': '808080',
          'navy': '000080', 'teal': '008080', 'maroon': '800000', 'darkred': '8B0000', 'darkblue': '00008B',
          'darkgreen': '006400', 'darkgray': 'A9A9A9', 'darkgrey': 'A9A9A9', 'darkorange': 'FF8C00',
          'auto': 'auto'}
HIGHLIGHTS = {h.lower(): h for h in 'black blue cyan green magenta red yellow white darkBlue darkCyan '
                                   'darkGreen darkMagenta darkRed darkYellow darkGray lightGray none'.split()}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        sys.exit(f'ERROR: {message}\n\n{__doc__}')


def parse():
    p = Parser(add_help=False)
    p.add_argument('src')
    p.add_argument('out')
    p.add_argument('--paragraph', action='append')
    p.add_argument('--paragraph-containing')
    p.add_argument('--occurrence', type=int)
    p.add_argument('--all', action='store_true')
    p.add_argument('--part', default='word/document.xml')
    p.add_argument('--color')
    p.add_argument('--size')
    p.add_argument('--highlight')
    p.add_argument('--font')
    for flag in ('bold', 'italic', 'underline'):
        p.add_argument(f'--{flag}', dest=flag, action='store_const', const=True)
        p.add_argument(f'--no-{flag}', dest=flag, action='store_const', const=False)
    a = p.parse_args()
    if (a.paragraph is None) == (a.paragraph_containing is None):
        p.error('give exactly one of --paragraph N or --paragraph-containing TEXT')
    if a.paragraph is not None:
        try:
            a.paragraph = [int(n) for item in a.paragraph for n in item.replace(' ', '').split(',') if n]
        except ValueError:
            p.error('--paragraph takes numbers, for example --paragraph 3 or --paragraph 3,7,12')
    return a


def wanted_properties(a):
    out, summary = {}, []
    if a.color is not None:
        value = COLORS.get(a.color.lower().replace(' ', '').replace('-', ''), a.color.lstrip('#').upper())
        if value != 'auto' and not re.fullmatch(r'[0-9A-F]{6}', value):
            sys.exit(f'ERROR: --color {a.color!r}: use six hex digits such as FF0000, or a name: {", ".join(COLORS)}')
        out['color'] = f'<w:color w:val="{value}"/>'
        summary.append('color=' + value)
    for flag, base in (('bold', 'b'), ('italic', 'i')):
        on = getattr(a, flag)
        if on is not None:
            val = '' if on else ' w:val="0"'
            out[base] = f'<w:{base}{val}/>'
            out[base + 'Cs'] = f'<w:{base}Cs{val}/>'
            summary.append(flag + ('' if on else '=off'))
    if a.underline is not None:
        out['u'] = f'<w:u w:val="{"single" if a.underline else "none"}"/>'
        summary.append('underline' + ('' if a.underline else '=off'))
    if a.size is not None:
        try:
            half = round(float(a.size) * 2)
        except ValueError:
            half = 0
        if half < 2 or half > 3276:
            sys.exit(f'ERROR: --size {a.size!r}: give points, for example 14 or 10.5')
        out['sz'] = f'<w:sz w:val="{half}"/>'
        out['szCs'] = f'<w:szCs w:val="{half}"/>'
        summary.append('size=' + a.size)
    if a.highlight is not None:
        name = HIGHLIGHTS.get(a.highlight.lower())
        if name is None:
            sys.exit(f'ERROR: --highlight {a.highlight!r}: use one of {", ".join(HIGHLIGHTS.values())}')
        out['highlight'] = f'<w:highlight w:val="{name}"/>'
        summary.append('highlight=' + name)
    if a.font is not None:
        f = ooxml.escape(a.font, {'"': '&quot;'})
        out['rFonts'] = f'<w:rFonts w:ascii="{f}" w:hAnsi="{f}" w:eastAsia="{f}" w:cs="{f}"/>'
        summary.append('font=' + a.font)
    if not out:
        sys.exit('ERROR: no format given (--color, --bold, --italic, --underline, --size, --highlight, --font)')
    return out, summary


def rank(tag):
    name = tag[2:] if tag.startswith('w:') else ''
    return RANK.get(name, LAST if name == 'rPrChange' else FOREIGN)


def rpr_with(existing, props):
    inner = ''
    if existing is not None:
        inner = re.sub(r'^<w:rPr(?:\s[^>]*)?/>$', '', existing)
        inner = re.sub(r'^<w:rPr(?:\s[^>]*)?>|</w:rPr>$', '', inner)
    kids = [(t, x) for t, x in ooxml.top_children(inner) if t[2:] not in props]
    for name, xml in props.items():
        at = next((i for i, (t, _) in enumerate(kids) if rank(t) > RANK[name]), len(kids))
        kids.insert(at, (f'w:{name}', xml))
    return '<w:rPr>' + ''.join(x for _, x in kids) + '</w:rPr>'


def format_run(match, props):
    opening = match.group(0)[:match.start(1) - match.start(0)]
    body = match.group(1)
    kids = ooxml.top_children(body)
    if kids and kids[0][0] == 'w:rPr' and body.startswith(kids[0][1]):
        return opening + rpr_with(kids[0][1], props) + body[len(kids[0][1]):] + '</w:r>'
    return opening + rpr_with(None, props) + body + '</w:r>'


def format_paragraph(par, props):
    runs = 0

    def run(m):
        nonlocal runs
        runs += 1
        return format_run(m, props)

    par = re.sub(r'<w:r(?=[\s>])[^>]*?(?<!/)>(.*?)</w:r>', run, par, flags=re.S)
    opening = re.match(r'<w:p(?=[\s>])[^>]*?>', par).group(0)
    body = par[len(opening):]
    kids = ooxml.top_children(body)
    mark = False
    if kids and kids[0][0] == 'w:pPr' and body.startswith(kids[0][1]):
        ppr = kids[0][1]
        inner = re.sub(r'^<w:pPr(?:\s[^>]*)?>|</w:pPr>$', '', ppr)
        rpr = next((x for t, x in ooxml.top_children(inner) if t == 'w:rPr'), None)
        if rpr is not None:
            par = opening + body.replace(ppr, ppr.replace(rpr, rpr_with(rpr, props), 1), 1)
            mark = True
    return par, runs, mark


def main():
    a = parse()
    props, summary = wanted_properties(a)
    ooxml.need_zip(a.src, 'IN')
    ooxml.need_distinct(a.src, a.out)
    xml = ooxml.read_part(a.src, a.part)
    if 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"' not in xml:
        sys.exit(f'ERROR: {a.part} is not a Word text part (no w: namespace).')
    pars = ooxml.paragraph_matches(xml, ooxml.DOCX)
    texts = [ooxml.paragraph_text(m.group(0), ooxml.DOCX) for m in pars]
    if a.paragraph is not None:
        missing = [n for n in a.paragraph if not 1 <= n <= len(pars)]
        if missing:
            sys.exit(f'ERROR: paragraph {missing[0]} does not exist; {a.part} has {len(pars)} paragraphs. Nothing changed.')
        picked = sorted(set(a.paragraph))
    else:
        hits = [n for n, t in enumerate(texts, 1) if a.paragraph_containing.lower() in t.lower()]
        if not hits:
            sys.exit(ooxml.no_text_match_message(texts, a.paragraph_containing, a.part))
        if a.occurrence is not None:
            if not 1 <= a.occurrence <= len(hits):
                sys.exit(f'ERROR: --occurrence {a.occurrence}: only {len(hits)} paragraph(s) contain that text.')
            picked = [hits[a.occurrence - 1]]
        elif a.all or len(hits) == 1:
            picked = hits
        else:
            shown = '; '.join(f'{n}: {ooxml.snippet(texts[n - 1], 60)!r}' for n in hits[:6])
            sys.exit(f'ERROR: {len(hits)} paragraphs contain that text ({shown}). '
                     'Add --occurrence K, --all, or use --paragraph N. Nothing changed.')
    out, at, total_runs, marks = [], 0, 0, 0
    for n in picked:
        m = pars[n - 1]
        par, runs, mark = format_paragraph(m.group(0), props)
        out += [xml[at:m.start()], par]
        at = m.end()
        total_runs += runs
        marks += mark
    out.append(xml[at:])
    new_xml = ''.join(out)
    if new_xml == xml:
        sys.exit('ERROR: the paragraph already has that formatting; nothing to change, nothing written.')
    what = ' '.join(summary)
    shown = ', '.join(map(str, picked)) if len(picked) <= 12 else f'{picked[0]} to {picked[-1]}'
    print(f'formatted {len(picked)} of {len(pars)} paragraphs ({shown}): {total_runs} run(s), '
          f'{marks} paragraph mark(s); {what}')
    ooxml.repack(a.src, a.out, {a.part: new_xml.encode('utf-8')})


if __name__ == '__main__':
    ooxml.cli(main)
