"""Unit tests for the xlsx and pptx skills' scripts: python3 -m unittest discover -s tests/unit"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SKILLS = os.path.join(ROOT, 'skills')


def run(skill, script, *args):
    r = subprocess.run([sys.executable, os.path.join(SKILLS, skill, 'scripts', script), *args], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return r.returncode, r.stdout + r.stderr


def parts_of(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n).decode('utf-8', 'replace') if n.endswith(('.xml', '.rels')) else z.read(n) for n in z.namelist()}


def rewrite(src, dst, edit):
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zout:
        for n in zin.namelist():
            zout.writestr(n, edit(n, zin.read(n)))


class Xlsx(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.dir = self.tmp.name
        spec = {'sheets': [{'name': 'Budget', 'header': True, 'formats': {'C': '#,##0.00'},
                            'rows': [['Item', 'Qty', 'Price', 'Total'], ['Pens', 10, 1.5, '=B2*C2'], ['Pads', 4, 3, '=B3*C3']]},
                           {'name': 'Notes', 'rows': [['a']]}]}
        with open(os.path.join(d, 'spec.json'), 'w') as f:
            json.dump(spec, f)
        code, out = run('xlsx', 'xlsx_new.py', os.path.join(d, 'spec.json'), os.path.join(d, 'plain.xlsx'))
        self.assertEqual(code, 0, out)

        def add_chain(name, data):
            if name == '[Content_Types].xml':
                return data.replace(b'</Types>', b'<Override PartName="/xl/calcChain.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.calcChain+xml"/></Types>')
            if name == 'xl/_rels/workbook.xml.rels':
                return data.replace(b'</Relationships>', b'<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/calcChain" Target="calcChain.xml"/></Relationships>')
            if name == 'xl/workbook.xml':
                return data.replace(b'<calcPr fullCalcOnLoad="1"/>', b'<calcPr calcId="191029"/>')
            return data
        self.src = os.path.join(d, 'book.xlsx')
        rewrite(os.path.join(d, 'plain.xlsx'), self.src, add_chain)
        with zipfile.ZipFile(self.src, 'a') as z:
            z.writestr('xl/calcChain.xml', '<calcChain xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><c r="D2" i="1"/></calcChain>')
        self.out = os.path.join(d, 'out.xlsx')

    def tearDown(self):
        self.tmp.cleanup()

    def test_set_number_text_formula_and_new_cells(self):
        code, out = run('xlsx', 'xlsx_set.py', self.src, self.out, 'Budget', 'B2', '20', 'A3', 'Notepads & ink', 'D5', '=SUM(D2:D3)', 'C4', '7', 'E1', 'Note')
        self.assertEqual(code, 0, out)
        self.assertIn('checks passed', out)
        xml = parts_of(self.out)['xl/worksheets/sheet1.xml']
        self.assertIn('<c r="B2"><v>20</v></c>', xml)
        self.assertIn('<c r="A3" t="inlineStr"><is><t xml:space="preserve">Notepads &amp; ink</t></is></c>', xml)
        self.assertIn('<row r="5"><c r="D5"><f>SUM(D2:D3)</f></c></row>', xml)
        self.assertRegex(xml, r'<row r="4"[^>]*><c r="C4" s="\d+"><v>7</v></c></row>')
        self.assertIn('<c r="E1" t="inlineStr">', xml)
        self.assertRegex(xml, r'<c r="D1"[^>]*>.*?</c><c r="E1"')
        wb = parts_of(self.out)['xl/workbook.xml']
        self.assertIn('fullCalcOnLoad="1"', wb)
        before, after = parts_of(self.src), parts_of(self.out)
        for name in before:
            if name not in ('xl/worksheets/sheet1.xml', 'xl/workbook.xml'):
                self.assertEqual(before[name], after[name], name)
        code, dump = run('xlsx', 'xlsx_dump.py', self.out)
        self.assertIn('B2\t20', dump)
        self.assertIn('D5\t=SUM(D2:D3)', dump)

    def test_formula_to_value_drops_calc_chain(self):
        code, out = run('xlsx', 'xlsx_set.py', self.src, self.out, 'Budget', 'D2', '15')
        self.assertEqual(code, 0, out)
        names = parts_of(self.out)
        self.assertNotIn('xl/calcChain.xml', names)
        self.assertNotIn('calcChain', names['xl/_rels/workbook.xml.rels'])
        self.assertNotIn('calcChain', names['[Content_Types].xml'])

    def test_text_flag_and_leading_zero(self):
        code, out = run('xlsx', 'xlsx_set.py', self.src, self.out, 'Budget', 'A2', '0012', 'A3', '55', '--text')
        self.assertEqual(code, 0, out)
        xml = parts_of(self.out)['xl/worksheets/sheet1.xml']
        self.assertIn('t="inlineStr"><is><t xml:space="preserve">0012<', xml)
        self.assertIn('t="inlineStr"><is><t xml:space="preserve">55<', xml)

    def test_bad_input_has_no_traceback(self):
        cases = [(self.src, self.out, 'Nope', 'A1', '1'), (self.src, self.out, 'Budget', 'ZZZZ1', '1'),
                 (self.src, self.out, 'Budget', 'A1'), (os.path.join(self.dir, 'x'), self.out, 'Budget', 'A1', '1'),
                 (self.dir, self.out, 'Budget', 'A1', '1')]
        for args in cases:
            code, out = run('xlsx', 'xlsx_set.py', *args)
            self.assertEqual(code, 1, args)
            self.assertTrue(out.startswith('ERROR:') or out.startswith('xlsx_set.py'), out)
            self.assertNotIn('Traceback', out)
        for script, args in (('xlsx_dump.py', [os.path.join(self.dir, 'spec.json')]), ('xlsx_dump.py', [self.src, 'Nope']),
                             ('xlsx_check.py', [self.dir]), ('xlsx_new.py', [os.path.join(self.dir, 'spec.json'), self.out, 'extra']),
                             ('xlsx_new.py', [os.path.join(self.dir, 'missing.json'), self.out])):
            code, out = run('xlsx', script, *args)
            self.assertEqual(code, 1, (script, args))
            self.assertNotIn('Traceback', out)

    def test_new_workbook_with_bad_spec(self):
        bad = os.path.join(self.dir, 'bad.json')
        with open(bad, 'w') as f:
            f.write("{'sheets': [")
        code, out = run('xlsx', 'xlsx_new.py', bad, self.out)
        self.assertEqual(code, 1)
        self.assertIn('not valid JSON', out)


class Pptx(unittest.TestCase):
    SLIDE = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
             'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
             '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
             '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Body"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/>'
             '<a:p><a:r><a:rPr lang="en-US"/><a:t>Revenue grew </a:t></a:r><a:r><a:rPr lang="en-US" b="1"/><a:t>12%</a:t></a:r><a:r><a:t> in Q3</a:t></a:r></a:p>'
             '<a:p><a:r><a:t>TEXT</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.dir = self.tmp.name
        self.src = os.path.join(d, 'deck.pptx')
        P = 'http://schemas.openxmlformats.org/'
        parts = {
            '[Content_Types].xml': f'<?xml version="1.0"?><Types xmlns="{P}package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
                                   '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
                                   '<Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
                                   '<Override PartName="/ppt/slides/slide2.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/></Types>',
            '_rels/.rels': f'<?xml version="1.0"?><Relationships xmlns="{P}package/2006/relationships"><Relationship Id="rId1" Type="{P}officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/></Relationships>',
            'ppt/presentation.xml': f'<?xml version="1.0"?><p:presentation xmlns:p="{P}presentationml/2006/main" xmlns:r="{P}officeDocument/2006/relationships"><p:sldIdLst><p:sldId id="256" r:id="rId2"/><p:sldId id="257" r:id="rId1"/></p:sldIdLst></p:presentation>',
            'ppt/_rels/presentation.xml.rels': f'<?xml version="1.0"?><Relationships xmlns="{P}package/2006/relationships"><Relationship Id="rId1" Type="{P}officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/><Relationship Id="rId2" Type="{P}officeDocument/2006/relationships/slide" Target="slides/slide2.xml"/></Relationships>',
            'ppt/slides/slide1.xml': self.SLIDE.replace('TEXT', 'Second in show order'),
            'ppt/slides/slide2.xml': self.SLIDE.replace('TEXT', 'First in show order'),
        }
        with zipfile.ZipFile(self.src, 'w', zipfile.ZIP_DEFLATED) as z:
            for n, t in parts.items():
                z.writestr(n, t)
        self.out = os.path.join(d, 'out.pptx')

    def tearDown(self):
        self.tmp.cleanup()

    def test_replace_across_runs_on_one_slide(self):
        code, out = run('pptx', 'pptx_replace_text.py', self.src, self.out, 'grew 12%', 'grew 15%', '--slide', '1')
        self.assertEqual(code, 0, out)
        self.assertIn('slide 1', out)
        self.assertIn('checks passed', out)
        after, before = parts_of(self.out), parts_of(self.src)
        self.assertIn('Revenue grew 15%', ''.join(re.findall(r'<a:t>([^<]*)</a:t>', after['ppt/slides/slide2.xml'])))
        self.assertEqual(before['ppt/slides/slide1.xml'], after['ppt/slides/slide1.xml'])
        self.assertNotIn('b="1"', after['ppt/slides/slide2.xml'])

    def test_ambiguity_and_near_miss(self):
        code, out = run('pptx', 'pptx_replace_text.py', self.src, self.out, 'Revenue grew', 'x')
        self.assertEqual(code, 1)
        self.assertIn('2 times', out)
        code, out = run('pptx', 'pptx_replace_text.py', self.src, self.out, 'Revenue grew', 'Sales rose', '--all')
        self.assertEqual(code, 0, out)
        code, out = run('pptx', 'pptx_replace_text.py', self.src, self.out, 'Revenu grew 12 %', 'x')
        self.assertEqual(code, 1)
        self.assertIn('Similar: slide', out)
        self.assertNotIn('Traceback', out)

    def test_outline_and_bad_input(self):
        code, out = run('pptx', 'pptx_outline.py', self.src)
        self.assertEqual(code, 0, out)
        self.assertIn('== slide 1: ppt/slides/slide2.xml', out)
        for args in ([self.dir], [os.path.join(self.dir, 'nope.pptx')]):
            code, out = run('pptx', 'pptx_outline.py', *args)
            self.assertEqual(code, 1)
            self.assertTrue(out.startswith('ERROR:'), out)


if __name__ == '__main__':
    unittest.main()
