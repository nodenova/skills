"""docx_find.py FILE.docx TEXT [PART] -- print each paragraph containing TEXT,
its runs, and its exact XML (copy OLD strings for `ooxml.py replace` from here)."""
import re, sys, zipfile
z = zipfile.ZipFile(sys.argv[1]); part = sys.argv[3] if len(sys.argv) > 3 else 'word/document.xml'
xml = z.read(part).decode('utf-8'); needle = sys.argv[2]
for n, m in enumerate(re.finditer(r'<w:p[ >].*?</w:p>', xml, re.S), 1):
    p = m.group(0)
    runs = re.findall(r'<w:t(?: [^>]*)?>([^<]*)</w:t>', p)
    text = ''.join(runs)
    if needle.lower() in text.lower():
        print(f'--- paragraph {n}')
        print('text:', text)
        print('runs:', ' | '.join(repr(r) for r in runs))
        print(p if len(p) < 3000 else p[:3000] + ' ...[cut]')
