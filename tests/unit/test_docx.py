"""Unit tests for the docx skill's scripts: python3 -m unittest discover -s tests/unit"""
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from xml.etree import ElementTree

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SCRIPTS = os.path.join(ROOT, 'skills', 'docx', 'scripts')
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

TITLE = (
    '<w:p w:rsidR="00A1"><w:pPr><w:pStyle w:val="BodyText1"/><w:rPr><w:b/><w:bCs/>'
    '<w:color w:val="9AD5D3" w:themeColor="accent4" w:themeTint="99"/></w:rPr></w:pPr>'
    '<w:r w:rsidRPr="00331078"><w:rPr><w:b/><w:bCs/></w:rPr><w:t xml:space="preserve">Re: Invitation to Tender </w:t></w:r>'
    '<w:r><w:rPr><w:b/><w:bCs/><w:color w:val="000000" w:themeColor="text2"/></w:rPr><w:t xml:space="preserve">for </w:t></w:r>'
    '<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:b/><w:sz w:val="22"/></w:rPr><w:t>the Dev</w:t></w:r>'
    '<w:r><w:t>elopers’ ‘Hub’</w:t></w:r></w:p>'
)
BODY = (
    '<w:p><w:r><w:t>Dear Sir,</w:t></w:r></w:p>'
    '<w:p w:rsidR="0001"/>'
    '<w:p><w:r><w:t xml:space="preserve">Payment is due within </w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>30</w:t></w:r>'
    '<w:r><w:t xml:space="preserve"> days &amp; no later.</w:t></w:r></w:p>'
    '<w:p><w:r><w:t>Late payment incurs a fee.</w:t></w:r></w:p>'
    '<w:p><w:r><w:t>Late payment is not tolerated.</w:t></w:r></w:p>'
)
DOCUMENT = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
    f'<w:document xmlns:w="{W}"><w:body>{TITLE}{BODY}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr></w:body></w:document>'
)
PARTS = {
    '[Content_Types].xml': '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                           '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                           '<Default Extension="xml" ContentType="application/xml"/>'
                           '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
    '_rels/.rels': '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
    'word/_rels/document.xml.rels': '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
    'word/document.xml': DOCUMENT,
    'word/styles.xml': f'<?xml version="1.0" encoding="UTF-8"?><w:styles xmlns:w="{W}"/>',
}


def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return r.returncode, r.stdout + r.stderr


def read_text(path):
    with open(path, encoding='utf-8', newline='') as f:
        return f.read()


def read_bytes(path):
    with open(path, 'rb') as f:
        return f.read()


def parts_of(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


class DocxScripts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.src = os.path.join(self.dir, 'letter.docx')
        with zipfile.ZipFile(self.src, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, text in PARTS.items():
                z.writestr(name, text.encode('utf-8'))
        self.out = os.path.join(self.dir, 'out.docx')

    def tearDown(self):
        self.tmp.cleanup()

    def paragraphs(self, path):
        root = ElementTree.fromstring(parts_of(path)['word/document.xml'])
        return list(root.iter(f'{{{W}}}p'))

    def assertNoTraceback(self, text):
        self.assertNotIn('Traceback', text)
        self.assertTrue(text.startswith('ERROR:'), text)

    def test_format_title_with_mixed_run_colours(self):
        code, out = run('docx_format.py', self.src, self.out, '--paragraph-containing', 'Invitation to Tender', '--color', 'FF0000')
        self.assertEqual(code, 0, out)
        self.assertIn('4 run(s)', out)
        self.assertIn('1 paragraph mark(s)', out)
        self.assertIn('checks passed', out)
        before, after = parts_of(self.src), parts_of(self.out)
        for name in before:
            if name != 'word/document.xml':
                self.assertEqual(before[name], after[name], name)
        self.assertEqual(list(before), list(after))
        xml = after['word/document.xml'].decode('utf-8')
        self.assertTrue(xml.startswith('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'))
        title = self.paragraphs(self.out)[0]
        runs = title.findall(f'{{{W}}}r')
        self.assertEqual(len(runs), 4)
        for r in runs:
            colors = r.findall(f'{{{W}}}rPr/{{{W}}}color')
            self.assertEqual([c.attrib for c in colors], [{f'{{{W}}}val': 'FF0000'}])
        mark = title.find(f'{{{W}}}pPr/{{{W}}}rPr')
        self.assertEqual([c.tag.split('}')[1] for c in mark], ['b', 'bCs', 'color'])
        self.assertEqual(mark.find(f'{{{W}}}color').attrib, {f'{{{W}}}val': 'FF0000'})
        self.assertNotIn('themeColor', xml.split('Dear Sir')[0])
        self.assertIn('<w:r><w:rPr><w:color w:val="FF0000"/></w:rPr><w:t>elopers', xml)

    def test_format_keeps_schema_order(self):
        code, out = run('docx_format.py', self.src, self.out, '--paragraph', '1', '--color', 'blue', '--bold', '--size', '14',
                        '--highlight', 'yellow', '--underline', '--italic', '--font', 'Calibri')
        self.assertEqual(code, 0, out)
        order = 'rStyle rFonts b bCs i iCs color sz szCs highlight u'.split()
        for r in self.paragraphs(self.out)[0].findall(f'{{{W}}}r'):
            names = [c.tag.split('}')[1] for c in r.find(f'{{{W}}}rPr')]
            self.assertEqual(names, [n for n in order if n in names], names)
            self.assertEqual(sorted(names), sorted(set(order) - {'rStyle'}))

    def test_format_takes_every_paragraph_given(self):
        code, out = run('docx_format.py', self.src, self.out, '--paragraph', '2', '--paragraph', '5,6', '--color', 'dark red')
        self.assertEqual(code, 0, out)
        self.assertIn('formatted 3 of 6 paragraphs (2, 5, 6)', out)
        coloured = {''.join(t.text for t in p.iter(f'{{{W}}}t')): {c.attrib[f'{{{W}}}val'] for c in p.iter(f'{{{W}}}color')}
                    for p in self.paragraphs(self.out)}
        self.assertEqual(coloured['Dear Sir,'], {'8B0000'})
        self.assertEqual(coloured['Late payment incurs a fee.'], {'8B0000'})
        self.assertEqual(coloured['Late payment is not tolerated.'], {'8B0000'})
        self.assertEqual(coloured['Payment is due within 30 days & no later.'], set())

    def test_a_table_row_as_text_points_at_one_cell(self):
        code, out = run('docx_replace_text.py', self.src, self.out, 'Dear Sir,\tLate payment', 'x')
        self.assertEqual(code, 1)
        self.assertIn('each cell is its own paragraph', out)

    def test_format_needs_one_choice_when_ambiguous(self):
        code, out = run('docx_format.py', self.src, self.out, '--paragraph-containing', 'Late payment', '--bold')
        self.assertEqual(code, 1)
        self.assertIn('2 paragraphs', out)
        self.assertFalse(os.path.exists(self.out))
        code, out = run('docx_format.py', self.src, self.out, '--paragraph-containing', 'Late payment', '--occurrence', '2', '--no-bold')
        self.assertEqual(code, 0, out)
        paragraphs = self.paragraphs(self.out)
        self.assertIn(f'{{{W}}}b', [c.tag for c in paragraphs[5].find(f'{{{W}}}r/{{{W}}}rPr')])
        self.assertEqual(paragraphs[5].find(f'{{{W}}}r/{{{W}}}rPr/{{{W}}}b').attrib, {f'{{{W}}}val': '0'})

    def test_format_errors_are_one_line(self):
        for args in (['--paragraph-containing', 'Invitation', '--color', 'notacolour'],
                     ['--paragraph-containing', 'Invitatoin to Tender', '--color', 'red'],
                     ['--paragraph', '99', '--bold'],
                     ['--paragraph-containing', 'Invitation'],
                     ['--bold']):
            code, out = run('docx_format.py', self.src, self.out, *args)
            self.assertEqual(code, 1, args)
            self.assertNoTraceback(out)
        code, out = run('docx_format.py', self.dir, self.out, '--paragraph', '1', '--bold')
        self.assertEqual(code, 1)
        self.assertNoTraceback(out)
        code, out = run('docx_format.py', self.src, self.src, '--paragraph', '1', '--bold')
        self.assertNoTraceback(out)
        code, out = run('docx_format.py', self.src, self.out, '--paragraph-containing', 'Invitatoin to Tender', '--color', 'red')
        self.assertIn('Similar: paragraph 1', out)

    def test_replace_text_across_runs(self):
        code, out = run('docx_replace_text.py', self.src, self.out, 'within 30 days', 'within 14 days')
        self.assertEqual(code, 0, out)
        self.assertIn('paragraph 4', out)
        paragraphs = self.paragraphs(self.out)
        text = ''.join(t.text or '' for t in paragraphs[3].iter(f'{{{W}}}t'))
        self.assertEqual(text, 'Payment is due within 14 days & no later.')
        xml = parts_of(self.out)['word/document.xml'].decode('utf-8')
        self.assertIn('<w:r><w:t xml:space="preserve">Payment is due within 14 days</w:t></w:r>', xml)
        self.assertEqual(len(paragraphs[3].findall(f'{{{W}}}r')), 2)
        code, out = run('docx_replace_text.py', self.src, self.out, 'due within 30', 'due within 7')
        self.assertEqual(code, 0, out)
        text = ''.join(t.text or '' for t in self.paragraphs(self.out)[3].iter(f'{{{W}}}t'))
        self.assertEqual(text, 'Payment is due within 7 days & no later.')
        self.assertEqual(len(self.paragraphs(self.out)[3].findall(f'{{{W}}}r')), 2)

    def test_replace_text_amp_and_all(self):
        code, out = run('docx_replace_text.py', self.src, self.out, 'Late payment', 'Delay')
        self.assertEqual(code, 1)
        self.assertIn('2 times', out)
        code, out = run('docx_replace_text.py', self.src, self.out, 'Late payment', 'Delay', '--all')
        self.assertEqual(code, 0, out)
        code, out = run('docx_replace_text.py', self.out, os.path.join(self.dir, 'o2.docx'), '& no', 'and <no>')
        self.assertEqual(code, 0, out)
        self.assertIn('and &lt;no&gt; later', parts_of(os.path.join(self.dir, 'o2.docx'))['word/document.xml'].decode())

    def test_replace_text_near_miss_and_curly_quotes(self):
        code, out = run('docx_replace_text.py', self.src, self.out, "developers' 'Hub'", 'x')
        self.assertEqual(code, 1)
        self.assertNoTraceback(out)
        self.assertIn('curly/straight', out)
        self.assertIn('elopers’ ‘Hub’', out)
        code, out = run('docx_replace_text.py', self.src, self.out, 'Dev’elopers', 'x')
        self.assertEqual(code, 1)
        code, out = run('docx_replace_text.py', self.src, self.out, 'Payment is du within 30 days', 'x')
        self.assertIn('Similar: paragraph 4', out)

    def test_find_accepts_docx_folder_and_part(self):
        unpacked = os.path.join(self.dir, 'x')
        code, out = run('ooxml.py', 'unpack', self.src, unpacked)
        self.assertEqual(code, 0, out)
        part = os.path.join(unpacked, 'word', 'document.xml')
        for src in (self.src, unpacked, part):
            code, out = run('docx_find.py', src, 'invitation to tender')
            self.assertEqual(code, 0, (src, out))
            self.assertIn('--- paragraph 1', out)
            self.assertIn("'for ' [b bCs color=000000]", out)
            self.assertIn('mark: [b bCs color=9AD5D3]', out)
            self.assertNotIn('<w:p', out)
        code, out = run('docx_find.py', self.src, 'invitation', '--xml')
        self.assertIn('<w:rPr><w:b/><w:bCs/></w:rPr>', out)
        code, out = run('docx_find.py', unpacked, 'Dear', 'word/document.xml')
        self.assertEqual(code, 0, out)

    def test_find_bad_input_has_no_traceback(self):
        unpacked = os.path.join(self.dir, 'x')
        run('ooxml.py', 'unpack', self.src, unpacked)
        for args in ([self.src, 'nothing like this at all'], [self.src, 'x', 'word/header9.xml'],
                     [os.path.join(self.dir, 'missing.docx'), 'x'], [self.dir, 'x'],
                     [os.path.join(self.dir, 'x', 'word', 'document.xml'), 'Invitatoin to Tendr']):
            code, out = run('docx_find.py', *args)
            self.assertEqual(code, 1, args)
            self.assertNoTraceback(out)

    def test_find_paragraph_with_self_closing_neighbour(self):
        code, out = run('docx_find.py', self.src, 'Payment is due')
        self.assertIn('--- paragraph 4', out)
        code, out = run('docx_find.py', self.src, 'Dear Sir')
        self.assertIn('--- paragraph 2', out)

    def test_ooxml_replace_with_wrong_input(self):
        code, out = run('ooxml.py', 'replace', self.src, '<w:t>x</w:t>', '<w:t>y</w:t>')
        self.assertEqual(code, 1)
        self.assertNoTraceback(out)
        self.assertIn('ooxml.py unpack FILE DIR', out)
        code, out = run('ooxml.py', 'replace', '/x/word/document.xml', 'a', 'b')
        self.assertNoTraceback(out)
        self.assertIn('shell variable was empty', out)
        code, out = run('ooxml.py', 'replace', self.dir, 'a', 'b')
        self.assertIn('is a folder', out)

    def test_ooxml_replace_near_miss(self):
        unpacked = os.path.join(self.dir, 'x')
        run('ooxml.py', 'unpack', self.src, unpacked)
        part = os.path.join(unpacked, 'word', 'document.xml')
        old = '<w:r><w:rPr><w:b/><w:bCs/><w:color w:val="000000" w:themeColor="text2"/></w:rPr><w:t xml:space="preserve">for </w:t></w:r>'
        wrong = old.replace('<w:bCs/>', '<w:bCs"/>')
        code, out = run('ooxml.py', 'replace', part, wrong, 'x')
        self.assertEqual(code, 1)
        self.assertNoTraceback(out)
        self.assertIn('Closest text in the part', out)
        self.assertIn("the part has '' where OLD has '\"'", out)
        code, out = run('ooxml.py', 'replace', part, 'completely unrelated text here', 'x')
        self.assertIn('No similar text', out)
        before = read_text(part)
        code, out = run('ooxml.py', 'replace', part, '>Dear Sir,<', '>Dear Madam,<')
        self.assertEqual(code, 0, out)
        after = read_text(part)
        self.assertEqual(after, before.replace('>Dear Sir,<', '>Dear Madam,<'))
        self.assertIn('\r\n', after)

    def test_ooxml_other_commands_have_no_traceback(self):
        for args in (['unpack', os.path.join(self.dir, 'nope.docx'), self.dir], ['unpack', self.dir, self.dir],
                     ['pack', self.src, os.path.join(self.dir, 'nodir'), self.out],
                     ['pack', os.path.join(self.dir, 'x'), self.dir, self.out],
                     ['validate', os.path.join(self.dir, 'nope.docx')]):
            code, out = run('ooxml.py', *args)
            self.assertEqual(code, 1, args)
            self.assertNoTraceback(out)

    def test_accept_wrong_input(self):
        code, out = run('docx_accept.py', self.src)
        self.assertEqual(code, 1)
        self.assertNoTraceback(out)

    def test_copies_are_in_sync(self):
        shared = read_bytes(os.path.join(ROOT, 'shared', 'ooxml.py'))
        for skill in ('docx', 'xlsx', 'pptx'):
            self.assertEqual(shared, read_bytes(os.path.join(ROOT, 'skills', skill, 'scripts', 'ooxml.py')), skill)


if __name__ == '__main__':
    unittest.main()
