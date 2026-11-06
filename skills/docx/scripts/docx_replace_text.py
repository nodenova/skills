"""docx_replace_text.py IN.docx OUT.docx OLD NEW [--all] [--part PART]

Replace text in a Word document by its words, even when Word split it across
several runs. NEW takes the formatting of the run where OLD starts; nothing
else changes. OLD must occur once unless --all. OLD and NEW are plain text
(no XML, no escaping); "@file" reads the text from that file instead. Matching
is exact (case, quotes, spaces): if OLD is not found, the closest text is shown.
PART defaults to word/document.xml (word/header1.xml, word/footer1.xml, ...).
Writes OUT through the same checked pack as `ooxml.py pack`. Not a tracked change.
"""
import sys

import ooxml


def main():
    args = sys.argv[1:]
    every = '--all' in args
    args = [a for a in args if a != '--all']
    part = 'word/document.xml'
    if '--part' in args:
        i = args.index('--part')
        part = args[i + 1]
        del args[i:i + 2]
    if len(args) != 4:
        sys.exit(__doc__)
    src, out, old, new = args[0], args[1], ooxml.arg(args[2]), ooxml.arg(args[3])
    ooxml.need_zip(src, 'IN')
    ooxml.need_distinct(src, out)
    xml = ooxml.read_part(src, part)
    changed, count, paragraphs = ooxml.replace_text(xml, ooxml.DOCX, old, new, every, part)
    print(f'replaced {count} in paragraph{"s" if len(paragraphs) > 1 else ""} {", ".join(map(str, paragraphs))} of {part}')
    ooxml.repack(src, out, {part: changed.encode('utf-8')})


if __name__ == '__main__':
    ooxml.cli(main)
