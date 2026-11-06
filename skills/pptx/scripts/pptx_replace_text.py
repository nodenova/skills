"""pptx_replace_text.py IN.pptx OUT.pptx OLD NEW [--slide N] [--all] [--part PART] [--all-parts] [--fixed]

Replace text on slides by its words, even when PowerPoint split it across
several runs. NEW takes the formatting of the run where OLD starts; nothing
else changes. Searches every slide (or only slide N, numbered as in
pptx_outline.py, or one --part such as ppt/notesSlides/notesSlide1.xml for
speaker notes). --all-parts also searches slide layouts, masters and notes
(where date and footer placeholders often live). Text inside an auto-updating
date field (datetime1, ...) is a cached value PowerPoint refreshes on open;
--fixed turns such a field into plain text so NEW stays. OLD must occur once
unless --all. OLD and NEW are plain text
(no XML, no escaping); "@file" reads the text from that file instead. Matching
is exact: if OLD is not found, the closest text is shown. OUT is written by the
same checked pack as `ooxml.py pack`.
"""
import re
import sys
import zipfile

import ooxml
import pptx_outline


DATE_FIELD = re.compile(r'<a:fld\b[^>]*\btype="datetime[^"]*"[^>]*>.*?</a:fld>', re.S)


def natural(name):
    return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', name)]


def plain(field):
    field = re.sub(r'<a:pPr\b[^>]*/>|<a:pPr\b.*?</a:pPr>', '', field, count=1, flags=re.S)
    return re.sub(r'^<a:fld\b[^>]*>', '<a:r>', re.sub(r'</a:fld>$', '</a:r>', field))


def main():
    auto = 0
    args = sys.argv[1:]
    every = '--all' in args
    wide = '--all-parts' in args
    fixed = '--fixed' in args
    args = [a for a in args if a not in ('--all', '--all-parts', '--fixed')]
    options = {}
    for flag in ('--slide', '--part'):
        if flag in args:
            i = args.index(flag)
            options[flag] = args[i + 1]
            del args[i:i + 2]
    if len(args) != 4:
        sys.exit(__doc__)
    src, out, old, new = args[0], args[1], ooxml.arg(args[2]), ooxml.arg(args[3])
    ooxml.need_zip(src, 'IN')
    ooxml.need_distinct(src, out)
    with zipfile.ZipFile(src) as z:
        slides = pptx_outline.slides_in_show_order(z)
        if '--part' in options:
            parts = [(options['--part'], options['--part'])]
        elif '--slide' in options:
            chosen = [s for s in slides if str(s[0]) == options['--slide']]
            if not chosen:
                sys.exit(f'ERROR: slide {options["--slide"]} does not exist; the deck has {len(slides)} slides.')
            parts = [(f'slide {chosen[0][0]}', chosen[0][1])]
        else:
            parts = [(f'slide {s[0]}', s[1]) for s in slides]
            if wide:
                parts += [(n.rsplit('/', 1)[-1][:-4], n) for n in sorted(z.namelist(), key=natural)
                          if re.fullmatch(r'ppt/(?:slideLayouts/slideLayout|slideMasters/slideMaster|notesSlides/notesSlide|notesMasters/notesMaster|handoutMasters/handoutMaster)\d+\.xml', n)]
    xmls = {part: ooxml.read_part(src, part) for _, part in parts}
    texts, labels = [], []
    for label, part in parts:
        for n, t in enumerate(ooxml.paragraph_texts(xmls[part], ooxml.PPTX), 1):
            texts.append(t)
            labels.append(f'{label}, paragraph {n}')
    hits = [labels[i] for i, t in enumerate(texts) if old in t for _ in range(t.count(old))]
    if not old:
        sys.exit('ERROR: OLD text is empty.')
    if not hits:
        sys.exit(ooxml.no_text_match_message(texts, old, 'the deck' if len(parts) > 1 else parts[0][1], labels))
    if len(hits) > 1 and not every:
        sys.exit(f'ERROR: {old!r} occurs {len(hits)} times ({"; ".join(hits)}). Use --all, --slide N, or a longer OLD text that occurs once. Nothing changed.')
    changes = {}
    for label, part in parts:
        if any(old in t for t in ooxml.paragraph_texts(xmls[part], ooxml.PPTX)):
            xml = ooxml.replace_text(xmls[part], ooxml.PPTX, old, new, True, part)[0]
            fields = [m for m in DATE_FIELD.finditer(xml) if new and new in ooxml.paragraph_text(m.group(0), ooxml.PPTX)]
            if fields and fixed:
                xml = DATE_FIELD.sub(lambda m: plain(m.group(0)) if new in ooxml.paragraph_text(m.group(0), ooxml.PPTX) else m.group(0), xml)
            elif fields:
                auto += len(fields)
            changes[part] = xml.encode('utf-8')
    print(f'replaced {len(hits)} in {", ".join(sorted(set(h.split(",")[0] for h in hits)))}')
    if auto:
        print(f'note: {auto} of them sit in auto-updating date fields; PowerPoint shows the current date for those when it opens the file. Repeat with --fixed to make them plain text.')
    ooxml.repack(src, out, changes)


if __name__ == '__main__':
    ooxml.cli(main)
