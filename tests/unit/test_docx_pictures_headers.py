"""Tests for docx_images.py and docx_header.py: python3 -m unittest discover -s tests/unit"""
import os
import re
import tempfile
import unittest

from support import P, ROOT, get, jpeg, png, put, read_zip, run, text_of, write_zip

W = P + 'wordprocessingml/2006/main'
NS = f'xmlns:w="{W}" xmlns:r="{P}officeDocument/2006/relationships" xmlns:wp="{P}drawingml/2006/wordprocessingml/drawing" xmlns:a="{P}drawingml/2006/main" xmlns:pic="{P}drawingml/2006/picture"'


def drawing(rid, cx, cy, name, descr=''):
    return (f'<w:r><w:drawing><wp:inline><wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="1" name="{name}" descr="{descr}"/>'
            f'<a:graphic><a:graphicData><pic:pic><pic:blipFill><a:blip r:embed="{rid}"/><a:srcRect l="1000"/></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')


TYPES = (f'<?xml version="1.0"?><Types xmlns="{P}package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
         '<Default Extension="xml" ContentType="application/xml"/><Default Extension="jpeg" ContentType="image/jpeg"/>'
         '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
         '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/></Types>')
ROOT_RELS = f'<?xml version="1.0"?><Relationships xmlns="{P}package/2006/relationships"><Relationship Id="rId1" Type="{P}officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'


def rels(*items):
    return f'<?xml version="1.0"?><Relationships xmlns="{P}package/2006/relationships">' + ''.join(items) + '</Relationships>'


def rel(i, kind, target):
    return f'<Relationship Id="{i}" Type="{P}officeDocument/2006/relationships/{kind}" Target="{target}"/>'


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.out = os.path.join(self.dir, 'out.docx')

    def tearDown(self):
        self.tmp.cleanup()

    def path(self, name):
        return os.path.join(self.dir, name)

    def build(self, name, body, extra=None, doc_rels=None, types=TYPES):
        parts = {'[Content_Types].xml': types, '_rels/.rels': ROOT_RELS,
                 'word/document.xml': f'<?xml version="1.0"?><w:document {NS}><w:body>{body}</w:body></w:document>',
                 'word/_rels/document.xml.rels': doc_rels or rels()}
        parts.update(extra or {})
        write_zip(self.path(name), parts)
        return self.path(name)


class Images(Fixture):
    def setUp(self):
        super().setUp()
        body = ('<w:p><w:r><w:t>Questionnaire</w:t></w:r></w:p>'
                f'<w:p>{drawing("rId5", 1828800, 457200, "Picture 3", "Company logo")}</w:p><w:p><w:r><w:t>Section one</w:t></w:r></w:p>'
                '<w:sectPr><w:headerReference w:type="default" r:id="rId6"/><w:pgSz w:w="11906" w:h="16838"/></w:sectPr>')
        header = f'<?xml version="1.0"?><w:hdr {NS}><w:p>{drawing("rId1", 914400, 914400, "Logo header")}<w:r><w:t>Acme</w:t></w:r></w:p></w:hdr>'
        self.src = self.build('q.docx', body, {
            'word/header1.xml': header, 'word/_rels/header1.xml.rels': rels(rel('rId1', 'image', 'media/image1.jpeg')),
            'word/media/image1.jpeg': jpeg(480, 120), 'word/media/image2.png': png(40, 10)},
            rels(rel('rId5', 'image', 'media/image2.png'), rel('rId6', 'header', 'header1.xml')))

    def test_list_shows_where_size_and_alt(self):
        code, out = run('docx', 'docx_images.py', 'list', self.src)
        self.assertEqual(code, 0, out)
        self.assertIn('2 picture(s) using 2 image file(s)', out)
        self.assertIn('body, paragraph 2', out)
        self.assertIn('word/media/image2.png', out)
        self.assertIn('png 40x10 px', out)
        self.assertIn('2.00 x 0.50 in (1828800 x 457200 EMU), inline', out)
        self.assertIn('alt: Company logo', out)
        self.assertIn('default header', out)
        self.assertIn('jpeg 480x120 px', out)
        self.assertIn('before: Questionnaire', out)
        self.assertNotIn('\x89PNG', out)

    def test_list_without_pictures_and_bad_input(self):
        plain = self.build('plain.docx', '<w:p><w:r><w:t>x</w:t></w:r></w:p>')
        code, out = run('docx', 'docx_images.py', 'list', plain)
        self.assertEqual(code, 0)
        self.assertIn('No pictures', out)
        for args in (['list', self.dir], ['list'], ['replace', self.src]):
            code, out = run('docx', 'docx_images.py', *args)
            self.assertEqual(code, 1)
            self.assertNotIn('Traceback', out)

    def test_replace_other_format_updates_rels_types_and_keeps_size(self):
        new = self.path('new.png')
        put(new, png(100, 100))
        code, out = run('docx', 'docx_images.py', 'replace', self.src, self.out, '--image', 'word/media/image1.jpeg', '--with', new)
        self.assertEqual(code, 0, out)
        self.assertIn('checks passed', out)
        after, before = read_zip(self.out), read_zip(self.src)
        self.assertNotIn('word/media/image1.jpeg', after)
        self.assertEqual(after['word/media/image1.png'], png(100, 100))
        self.assertIn('Target="media/image1.png"', text_of(after, 'word/_rels/header1.xml.rels'))
        self.assertIn('Id="rId1"', text_of(after, 'word/_rels/header1.xml.rels'))
        self.assertIn('Extension="png"', text_of(after, '[Content_Types].xml'))
        self.assertEqual(before['word/header1.xml'], after['word/header1.xml'])
        self.assertEqual(before['word/document.xml'], after['word/document.xml'])
        self.assertEqual(before['word/media/image2.png'], after['word/media/image2.png'])
        code, out = run('docx', 'docx_images.py', 'list', self.out)
        self.assertIn('png 100x100 px', out)

    def test_replace_same_format_by_basename(self):
        new = self.path('new.png')
        put(new, png(10, 40))
        code, out = run('docx', 'docx_images.py', 'replace', self.src, self.out, '--image', 'image2.png', '--with', new, '--keep-size')
        self.assertEqual(code, 0, out)
        after = read_zip(self.out)
        self.assertEqual(after['word/media/image2.png'], png(10, 40))
        self.assertEqual(after['word/document.xml'], read_zip(self.src)['word/document.xml'])
        self.assertNotIn('[Content_Types].xml', out.split('changed:')[-1])

    def test_fit_keeps_proportions_inside_old_box(self):
        new = self.path('new.png')
        put(new, png(100, 100))
        code, out = run('docx', 'docx_images.py', 'replace', self.src, self.out, '--image', 'word/media/image2.png', '--with', new, '--fit')
        self.assertEqual(code, 0, out)
        doc = text_of(read_zip(self.out), 'word/document.xml')
        self.assertEqual(len(re.findall(r'cx="457200" cy="457200"', doc)), 2)
        self.assertNotIn('1828800', doc)
        self.assertNotIn('srcRect', doc)

    def test_replace_errors(self):
        new = self.path('new.png')
        put(new, png(5, 5))
        svg = self.path('a.svg')
        put(svg, '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>')
        text = self.path('t.png')
        put(text, 'not an image')
        for args, word in ((['--image', 'word/media/nope.png', '--with', new], 'no image file'),
                           (['--image', 'word/media/image2.png', '--with', svg], 'SVG'),
                           (['--image', 'word/media/image2.png', '--with', text], 'not a PNG'),
                           (['--image', 'word/media/image2.png', '--with', self.path('missing.png')], 'not found'),
                           (['--image', 'word/media/image2.png', '--with', new, '--fit', '--keep-size'], 'docx_images.py')):
            code, out = run('docx', 'docx_images.py', 'replace', self.src, self.out, *args)
            self.assertEqual(code, 1, args)
            self.assertIn(word, out)
            self.assertNotIn('Traceback', out)
        self.assertFalse(os.path.exists(self.out))

    def test_find_hint_for_pictures(self):
        code, out = run('docx', 'docx_find.py', self.src, 'logo')
        self.assertEqual(code, 1)
        self.assertIn('docx_images.py list', out)


class Header(Fixture):
    def test_new_header_in_body_and_paragraph_sections(self):
        body = ('<w:p><w:r><w:t>One</w:t></w:r></w:p><w:p><w:pPr><w:sectPr><w:pgSz w:w="1" w:h="2"/></w:sectPr></w:pPr></w:p>'
                '<w:p><w:r><w:t>Two</w:t></w:r></w:p><w:sectPr/>')
        src = self.build('d.docx', body, {'word/styles.xml': f'<w:styles xmlns:w="{W}"><w:style w:type="paragraph" w:styleId="Header"/></w:styles>'})
        code, out = run('docx', 'docx_header.py', src, self.out, '--text', 'NodeNova & Co', '--align', 'center')
        self.assertEqual(code, 0, out)
        self.assertIn('checks passed', out)
        after = read_zip(self.out)
        doc = text_of(after, 'word/document.xml')
        self.assertEqual(doc.count('<w:headerReference w:type="default"'), 1)
        self.assertIn('<w:sectPr><w:headerReference', doc)
        header = text_of(after, 'word/header1.xml')
        self.assertIn('NodeNova &amp; Co', header)
        self.assertIn('<w:jc w:val="center"/>', header)
        self.assertIn('<w:pStyle w:val="Header"/>', header)
        self.assertIn('/word/header1.xml', text_of(after, '[Content_Types].xml'))
        self.assertIn('Target="header1.xml"', text_of(after, 'word/_rels/document.xml.rels'))
        self.assertEqual(read_zip(self.out)['word/styles.xml'], read_zip(src)['word/styles.xml'])

    def test_footer_is_separate_from_header(self):
        src = self.build('d.docx', '<w:p/><w:sectPr/>')
        code, out = run('docx', 'docx_header.py', src, self.out, '--text', 'Page footer', '--footer')
        self.assertEqual(code, 0, out)
        after = read_zip(self.out)
        self.assertIn('<w:footerReference w:type="default"', text_of(after, 'word/document.xml'))
        self.assertIn('<w:ftr ', text_of(after, 'word/footer1.xml'))
        self.assertNotIn('word/header1.xml', after)

    def test_first_page_and_even_headers(self):
        body = '<w:p/><w:sectPr><w:titlePg/></w:sectPr>'
        settings = f'<w:settings xmlns:w="{W}"><w:evenAndOddHeaders/></w:settings>'
        src = self.build('d.docx', body, {'word/settings.xml': settings})
        code, out = run('docx', 'docx_header.py', src, self.out, '--text', 'NodeNova')
        self.assertEqual(code, 0, out)
        doc = text_of(read_zip(self.out), 'word/document.xml')
        for kind in ('default', 'first', 'even'):
            self.assertIn(f'<w:headerReference w:type="{kind}"', doc)
        only = os.path.join(self.dir, 'only.docx')
        code, out = run('docx', 'docx_header.py', src, only, '--text', 'NodeNova', '--type', 'first')
        self.assertEqual(code, 0, out)
        doc = text_of(read_zip(only), 'word/document.xml')
        self.assertIn('w:type="first"', doc)
        self.assertNotIn('w:type="default"', doc)

    def existing(self, header_body):
        return self.build('e.docx', '<w:p/><w:sectPr><w:headerReference w:type="default" r:id="rId3"/></w:sectPr>',
                          {'word/header2.xml': f'<w:hdr {NS}>{header_body}</w:hdr>'}, rels(rel('rId3', 'header', 'header2.xml')),
                          TYPES.replace('/word/header1.xml', '/word/header2.xml'))

    def test_existing_header_empty_paragraph_is_filled(self):
        src = self.existing('<w:p><w:pPr><w:pStyle w:val="Header"/></w:pPr></w:p>')
        code, out = run('docx', 'docx_header.py', src, self.out, '--text', 'NodeNova', '--align', 'right')
        self.assertEqual(code, 0, out)
        after = read_zip(self.out)
        header = text_of(after, 'word/header2.xml')
        self.assertEqual(header.count('<w:p>') + header.count('<w:p '), 1)
        self.assertIn('<w:pStyle w:val="Header"/><w:jc w:val="right"/>', header)
        self.assertEqual(read_zip(src)['word/document.xml'], after['word/document.xml'])
        self.assertNotIn('word/header1.xml', after)

    def test_existing_header_with_picture_gets_added_paragraph_and_is_idempotent(self):
        pic = f'<w:p>{drawing("rId9", 100, 100, "Logo")}</w:p>'
        src = self.existing(pic)
        code, out = run('docx', 'docx_header.py', src, self.out, '--text', 'NodeNova')
        self.assertEqual(code, 0, out)
        header = text_of(read_zip(self.out), 'word/header2.xml')
        self.assertIn('<w:drawing>', header)
        self.assertTrue(header.endswith('<w:t xml:space="preserve">NodeNova</w:t></w:r></w:p></w:hdr>'))
        again = os.path.join(self.dir, 'again.docx')
        code, out = run('docx', 'docx_header.py', self.out, again, '--text', 'NodeNova')
        self.assertEqual(code, 0, out)
        self.assertIn('nothing to change', out)
        self.assertEqual(read_zip(again), read_zip(self.out))

    def test_replace_keeps_pictures_fields_and_run_format(self):
        header = (f'<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:b/></w:rPr><w:t>Old</w:t></w:r><w:r><w:t> title</w:t></w:r></w:p>'
                  f'<w:p>{drawing("rId9", 1, 1, "Logo")}</w:p><w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:t>PAGE</w:t></w:r></w:p>'
                  '<w:p><w:r><w:t>Second</w:t></w:r></w:p>')
        src = self.existing(header)
        code, out = run('docx', 'docx_header.py', src, self.out, '--text', 'NodeNova', '--replace')
        self.assertEqual(code, 0, out)
        header = text_of(read_zip(self.out), 'word/header2.xml')
        self.assertNotIn('Old', header)
        self.assertNotIn('Second', header)
        self.assertIn('<w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">NodeNova</w:t>', header)
        self.assertIn('<w:drawing>', header)
        self.assertIn('fldChar', header)

    def test_errors_are_one_line(self):
        src = self.build('d.docx', '<w:p/><w:sectPr/>')
        for args in ([src, self.out], [src, self.out, '--text', ' '], [src, self.out, '--text', 'x', '--align', 'middle'],
                     [self.dir, self.out, '--text', 'x'], [src, src, '--text', 'x']):
            code, out = run('docx', 'docx_header.py', *args)
            self.assertEqual(code, 1, args)
            self.assertNotIn('Traceback', out)

    def test_section_change_markup_is_ignored(self):
        body = ('<w:p/><w:sectPr><w:sectPrChange w:id="1"><w:sectPr><w:pgSz w:w="1" w:h="2"/></w:sectPr></w:sectPrChange></w:sectPr>')
        src = self.build('d.docx', body)
        code, out = run('docx', 'docx_header.py', src, self.out, '--text', 'NodeNova')
        self.assertEqual(code, 0, out)
        doc = text_of(read_zip(self.out), 'word/document.xml')
        self.assertEqual(doc.count('headerReference'), 1)
        self.assertTrue(doc.index('headerReference') < doc.index('sectPrChange'))


class Sync(unittest.TestCase):
    def test_images_copies_match_shared(self):
        shared = get(os.path.join(ROOT, 'shared', 'ooxml_images.py'))
        for skill in ('docx', 'pptx'):
            self.assertEqual(shared, get(os.path.join(ROOT, 'skills', skill, 'scripts', 'ooxml_images.py')), skill)


if __name__ == '__main__':
    unittest.main()
