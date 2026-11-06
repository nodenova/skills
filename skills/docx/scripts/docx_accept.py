"""docx_accept.py PART.xml -- accept every tracked change in one unpacked part."""
import re
import sys

import ooxml


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    p = sys.argv[1]
    ooxml.need_text_file(p, 'PART.xml')
    s = open(p, encoding='utf-8').read()
    s = re.sub(r'<w:del\b[^>]*/>|<w:del\b[^>]*>.*?</w:del>', '', s, flags=re.S)
    s = re.sub(r'<w:moveFrom\b[^>]*>.*?</w:moveFrom>', '', s, flags=re.S)
    s = re.sub(r'</?w:(ins|moveTo)\b[^>]*>', '', s)
    s = re.sub(r'<w:(moveFromRangeStart|moveFromRangeEnd|moveToRangeStart|moveToRangeEnd)\b[^>]*/>', '', s)
    s = re.sub(r'<w:(rPrChange|pPrChange|sectPrChange|tblPrChange|trPrChange|tcPrChange)\b[^>]*>.*?</w:\1>', '', s, flags=re.S)
    open(p, 'w', encoding='utf-8').write(s)
    print('accepted tracked changes in', p, '| left:', len(re.findall(r'<w:(ins|del|moveFrom|moveTo)\b', s)))


if __name__ == '__main__':
    ooxml.cli(main)
