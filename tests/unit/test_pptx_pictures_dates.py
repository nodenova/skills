"""Tests for pptx_images.py, the outline's date/footer marks and pptx_replace_text.py --all-parts."""
import os
import re
import tempfile
import unittest

from support import P, png, jpeg, put, read_zip, run, text_of, write_zip

A = P + 'drawingml/2006/main'
NS = f'xmlns:a="{A}" xmlns:r="{P}officeDocument/2006/relationships" xmlns:p="{P}presentationml/2006/main"'
PIC = ('<p:pic><p:nvPicPr><p:cNvPr id="4" name="Logo" descr="Company logo"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr>'
       '<p:blipFill><a:blip r:embed="rId2"/><a:srcRect t="5000"/><a:stretch/></p:blipFill>'
       '<p:spPr><a:xfrm><a:off x="1000000" y="500000"/><a:ext cx="2000000" cy="1000000"/></a:xfrm></p:spPr></p:pic>')
DATE = ('<p:sp><p:nvSpPr><p:cNvPr id="5" name="Date Placeholder 4"/><p:cNvSpPr/><p:nvPr><p:ph type="dt" sz="half" idx="10"/></p:nvPr></p:nvSpPr><p:spPr/>'
        '<p:txBody><a:bodyPr/><a:p><a:fld id="{1}" type="datetime1"><a:rPr lang="en-US"/><a:pPr><a:defRPr/></a:pPr><a:t>11/3/2026</a:t></a:fld><a:endParaRPr lang="en-US"/></a:p></p:txBody></p:sp>'
        '<p:sp><p:nvSpPr><p:cNvPr id="6" name="Footer Placeholder 5"/><p:cNvSpPr/><p:nvPr><p:ph type="ftr" idx="11"/></p:nvPr></p:nvSpPr><p:spPr/>'
        '<p:txBody><a:bodyPr/><a:p><a:r><a:t>Confidential</a:t></a:r></a:p></p:txBody></p:sp>')


def sp(body):
    return f'<?xml version="1.0"?><p:sld {NS}><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>{body}</p:spTree></p:cSld></p:sld>'


def rel(i, kind, target):
    return f'<Relationship Id="{i}" Type="{P}officeDocument/2006/relationships/{kind}" Target="{target}"/>'


def rels(*items):
    return f'<?xml version="1.0"?><Relationships xmlns="{P}package/2006/relationships">' + ''.join(items) + '</Relationships>'


TITLE = ('<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/>'
         '<a:p><a:r><a:t>Quarterly update</a:t></a:r></a:p></p:txBody></p:sp>')


class Deck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.src = os.path.join(self.dir, 'deck.pptx')
        self.out = os.path.join(self.dir, 'out.pptx')
        layout = sp(DATE.replace('11/3/2026', '1/1/2020')).replace('<p:cSld>', '<p:cSld name="Title Slide">')
        write_zip(self.src, {
            '[Content_Types].xml': f'<?xml version="1.0"?><Types xmlns="{P}package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                                   '<Default Extension="xml" ContentType="application/xml"/><Default Extension="jpeg" ContentType="image/jpeg"/></Types>',
            '_rels/.rels': f'<?xml version="1.0"?><Relationships xmlns="{P}package/2006/relationships"><Relationship Id="rId1" Type="{P}officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/></Relationships>',
            'ppt/presentation.xml': f'<?xml version="1.0"?><p:presentation {NS}><p:sldIdLst><p:sldId id="256" r:id="rId1"/><p:sldId id="257" r:id="rId2"/></p:sldIdLst></p:presentation>',
            'ppt/_rels/presentation.xml.rels': rels(rel('rId1', 'slide', 'slides/slide1.xml'), rel('rId2', 'slide', 'slides/slide2.xml')),
            'ppt/slides/slide1.xml': sp(TITLE + PIC + DATE),
            'ppt/slides/_rels/slide1.xml.rels': rels(rel('rId1', 'slideLayout', '../slideLayouts/slideLayout1.xml'), rel('rId2', 'image', '../media/image1.jpeg')),
            'ppt/slides/slide2.xml': sp(TITLE.replace('Quarterly update', 'Second') + DATE),
            'ppt/slides/_rels/slide2.xml.rels': rels(rel('rId1', 'slideLayout', '../slideLayouts/slideLayout1.xml')),
            'ppt/slideLayouts/slideLayout1.xml': layout,
            'ppt/slideLayouts/_rels/slideLayout1.xml.rels': rels(),
            'ppt/media/image1.jpeg': jpeg(300, 150),
        })

    def tearDown(self):
        self.tmp.cleanup()

    def test_list_pictures(self):
        code, out = run('pptx', 'pptx_images.py', 'list', self.src)
        self.assertEqual(code, 0, out)
        self.assertIn('1 picture(s) using 1 image file(s)', out)
        self.assertIn('slide 1', out)
        self.assertIn('ppt/media/image1.jpeg', out)
        self.assertIn('jpeg 300x150 px', out)
        self.assertIn('2.19 x 1.09 in (2000000 x 1000000 EMU)', out)
        self.assertIn('name: Logo  alt: Company logo', out)
        self.assertIn('near: Quarterly update', out)

    def test_replace_fit_centres_in_old_box(self):
        new = put(os.path.join(self.dir, 'logo.png'), png(100, 100))
        code, out = run('pptx', 'pptx_images.py', 'replace', self.src, self.out, '--image', 'ppt/media/image1.jpeg', '--with', new, '--fit')
        self.assertEqual(code, 0, out)
        after, before = read_zip(self.out), read_zip(self.src)
        slide = text_of(after, 'ppt/slides/slide1.xml')
        self.assertIn('<a:off x="1500000" y="500000"/><a:ext cx="1000000" cy="1000000"/>', slide)
        self.assertNotIn('srcRect', slide)
        self.assertIn('Target="../media/image1.png"', text_of(after, 'ppt/slides/_rels/slide1.xml.rels'))
        self.assertIn('Extension="png"', text_of(after, '[Content_Types].xml'))
        self.assertEqual(before['ppt/slides/slide2.xml'], after['ppt/slides/slide2.xml'])

    def test_replace_keeps_size_by_default(self):
        new = put(os.path.join(self.dir, 'logo.jpeg'), jpeg(10, 10))
        code, out = run('pptx', 'pptx_images.py', 'replace', self.src, self.out, '--image', 'image1.jpeg', '--with', new)
        self.assertEqual(code, 0, out)
        after = read_zip(self.out)
        self.assertEqual(after['ppt/media/image1.jpeg'], jpeg(10, 10))
        self.assertEqual(after['ppt/slides/slide1.xml'], read_zip(self.src)['ppt/slides/slide1.xml'])

    def test_outline_marks_placeholders_and_fields(self):
        code, out = run('pptx', 'pptx_outline.py', self.src)
        self.assertEqual(code, 0, out)
        self.assertIn('[Date Placeholder 4 (date placeholder)] {datetime1: 11/3/2026}', out)
        self.assertIn('[Footer Placeholder 5 (footer placeholder)] Confidential', out)
        self.assertNotIn('Title Slide', out)
        code, out = run('pptx', 'pptx_outline.py', self.src, '--layouts')
        self.assertIn('== ppt/slideLayouts/slideLayout1.xml "Title Slide"', out)
        self.assertIn('{datetime1: 1/1/2020}', out)
        self.assertNotIn('Quarterly update', out.split('== ppt/slideLayouts')[1])

    def test_replace_date_all_parts_and_fixed(self):
        code, out = run('pptx', 'pptx_replace_text.py', self.src, self.out, '11/3/2026', '11/6/2026', '--all')
        self.assertEqual(code, 0, out)
        self.assertIn('auto-updating date fields', out)
        self.assertIn('--fixed', out)
        code, out = run('pptx', 'pptx_replace_text.py', self.src, self.out, '1/1/2020', '11/6/2026')
        self.assertEqual(code, 1)
        self.assertIn('ERROR', out)
        code, out = run('pptx', 'pptx_replace_text.py', self.src, self.out, '1/1/2020', '11/6/2026', '--all-parts')
        self.assertEqual(code, 0, out)
        self.assertIn('slideLayout1', out)
        self.assertEqual(read_zip(self.src)['ppt/slides/slide1.xml'], read_zip(self.out)['ppt/slides/slide1.xml'])
        fixed = os.path.join(self.dir, 'fixed.pptx')
        code, out = run('pptx', 'pptx_replace_text.py', self.src, fixed, '11/3/2026', '11/6/2026', '--all', '--fixed')
        self.assertEqual(code, 0, out)
        self.assertNotIn('auto-updating', out)
        slide = text_of(read_zip(fixed), 'ppt/slides/slide1.xml')
        self.assertNotIn('<a:fld', slide)
        self.assertIn('<a:r><a:rPr lang="en-US"/><a:t>11/6/2026</a:t></a:r>', slide)
        self.assertNotIn('defRPr', slide)
        self.assertEqual(len(re.findall('11/6/2026', text_of(read_zip(fixed), 'ppt/slides/slide2.xml'))), 1)

    def test_images_errors(self):
        for args in (['list', self.dir], ['replace', self.src, self.out, '--image', 'nope.png', '--with', self.src]):
            code, out = run('pptx', 'pptx_images.py', *args)
            self.assertEqual(code, 1)
            self.assertNotIn('Traceback', out)


class NoSoffice(unittest.TestCase):
    def test_xlsx_check_says_so_when_soffice_is_missing(self):
        import subprocess
        import sys
        from support import SKILLS
        with tempfile.TemporaryDirectory() as d:
            book = os.path.join(d, 'b.xlsx')
            write_zip(book, {'[Content_Types].xml': '<Types/>'})
            r = subprocess.run([sys.executable, os.path.join(SKILLS, 'xlsx', 'scripts', 'xlsx_check.py'), book], capture_output=True, text=True,
                               env=dict(os.environ, PATH=d, PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(r.returncode, 1)
        self.assertIn('soffice', r.stderr)
        self.assertIn('xlsx_dump.py', r.stderr)
        self.assertNotIn('Traceback', r.stderr)


if __name__ == '__main__':
    unittest.main()
